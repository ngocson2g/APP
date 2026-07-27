# security_app/reporting/html_exporter.py
import json
import os
from typing import Any
from datetime import datetime

from security_app.reporting.exporters import build_stats_json

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security App - Compliance Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --primary: #4f46e5;
            --success: #10b981;
            --danger: #ef4444;
            --warn: #f59e0b;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1, h2, h3 { margin-top: 0; }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 2px solid var(--border);
        }
        .header .meta { color: var(--text-muted); font-size: 0.9em; }
        .grid-3 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }
        .card {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            border: 1px solid var(--border);
        }
        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            margin: 10px 0;
            color: var(--primary);
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: bold;
            text-transform: uppercase;
            color: white;
        }
        .badge.critical { background: var(--danger); }
        .badge.high { background: #ea580c; }
        .badge.medium { background: var(--warn); }
        .badge.low { background: #3b82f6; }
        .badge.unknown { background: var(--text-muted); }
        
        .status-ok { color: var(--success); font-weight: bold; }
        .status-fail { color: var(--danger); font-weight: bold; }
        
        .table-container {
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }
        th, td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        th {
            background: var(--bg);
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            font-size: 0.8rem;
        }
        tr:hover { background: #f1f5f9; }
        .charts-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 24px;
        }
        @media (max-width: 768px) {
            .charts-container { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>

<div class="container">
    <div class="header">
        <div>
            <h1>Compliance Report</h1>
            <div class="meta">Generated: __DATE__</div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 0.9em; color: var(--text-muted);">Compliance Score</div>
            <div style="font-size: 2rem; font-weight: bold; color: var(--primary);">__SCORE__ / 100</div>
            <div style="font-size: 1.2rem; font-weight: bold;">Grade: __GRADE__</div>
        </div>
    </div>

    <div class="grid-3">
        <div class="card">
            <h3>Total Rules</h3>
            <div class="stat-value">__TOTAL_RULES__</div>
            <div style="color: var(--text-muted)">Evaluated in this run</div>
        </div>
        <div class="card">
            <h3>Passed Rules</h3>
            <div class="stat-value" style="color: var(--success)">__ALL_OK__</div>
            <div style="color: var(--text-muted)">Pass rate: __PASS_RATE__%</div>
        </div>
        <div class="card">
            <h3>Failed Rules</h3>
            <div class="stat-value" style="color: var(--danger)">__WITH_FAILURES__</div>
            <div style="color: var(--text-muted)">Require attention</div>
        </div>
    </div>

    <div class="charts-container">
        <div class="card" style="position: relative; height: 350px;">
            <h3 style="text-align: center;">Rule Status Breakdown</h3>
            <canvas id="pieChart"></canvas>
        </div>
        <div class="card" style="position: relative; height: 350px;">
            <h3 style="text-align: center;">Severity Breakdown</h3>
            <canvas id="barChart"></canvas>
        </div>
    </div>

    <div class="card">
        <h3>All Rules Details</h3>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Rule ID</th>
                        <th>Severity</th>
                        <th>Title</th>
                        <th>Cmd OK</th>
                        <th>Cmd Fail</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="rulesTableBody">
                    <!-- Javascript will populate this -->
                </tbody>
            </table>
        </div>
    </div>
</div>

<script>
    // Data injected by Python
    const reportData = __DATA__;

    // Populate Table
    const tbody = document.getElementById('rulesTableBody');
    reportData.rules.forEach((r, idx) => {
        const tr = document.createElement('tr');
        
        const statusClass = r.status === 'ok' ? 'status-ok' : 'status-fail';
        const statusText = r.status.toUpperCase();
        const severityClass = r.severity.toLowerCase() || 'unknown';
        
        tr.innerHTML = `
            <td>${idx + 1}</td>
            <td><code>${r.id}</code></td>
            <td><span class="badge ${severityClass}">${r.severity}</span></td>
            <td>${r.title}</td>
            <td>${r.cmd_ok}</td>
            <td>${r.cmd_fail}</td>
            <td class="${statusClass}">${statusText}</td>
        `;
        tbody.appendChild(tr);
    });

    // Chart.js Configuration
    const summary = reportData.summary;
    const bySev = reportData.by_severity;
    
    // Pie Chart
    const ctxPie = document.getElementById('pieChart').getContext('2d');
    new Chart(ctxPie, {
        type: 'doughnut',
        data: {
            labels: ['Passed', 'Failed'],
            datasets: [{
                data: [summary.all_ok, summary.with_failures],
                backgroundColor: ['#10b981', '#ef4444'],
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });

    // Bar Chart
    const severities = ['critical', 'high', 'medium', 'low', 'unknown'];
    const passData = severities.map(s => bySev[s] ? bySev[s].rules_ok : 0);
    const failData = severities.map(s => bySev[s] ? (bySev[s].rules - bySev[s].rules_ok) : 0);

    const ctxBar = document.getElementById('barChart').getContext('2d');
    new Chart(ctxBar, {
        type: 'bar',
        data: {
            labels: severities.map(s => s.charAt(0).toUpperCase() + s.slice(1)),
            datasets: [
                {
                    label: 'Passed',
                    data: passData,
                    backgroundColor: '#10b981'
                },
                {
                    label: 'Failed',
                    data: failData,
                    backgroundColor: '#ef4444'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { stacked: true },
                y: { stacked: true }
            },
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
</script>
</body>
</html>
"""

def dump_stats_html(stats: dict[str, Any], path: str) -> None:
    data = build_stats_json(stats)
    summary = data.get("summary", {})
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html = HTML_TEMPLATE
    html = html.replace("__DATE__", now_str)
    html = html.replace("__SCORE__", str(summary.get("compliance_score", 0)))
    html = html.replace("__GRADE__", str(summary.get("compliance_grade", "F")))
    html = html.replace("__TOTAL_RULES__", str(summary.get("total_rules", 0)))
    html = html.replace("__ALL_OK__", str(summary.get("all_ok", 0)))
    html = html.replace("__WITH_FAILURES__", str(summary.get("with_failures", 0)))
    html = html.replace("__PASS_RATE__", str(summary.get("pass_rate", 0)))
    
    # Inject raw JSON data for the charts and table
    json_data = json.dumps(data, ensure_ascii=False)
    html = html.replace("__DATA__", json_data)
    
    if path == "-" or path.strip() == "":
        import sys
        sys.stdout.write(html + "\n")
        return
        
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
