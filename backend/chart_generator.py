def should_generate_chart(query: str, result: dict) -> bool:
    """Determine if query should generate a chart based on keywords and data structure"""
    if "error" in result or not result.get("rows"):
        return False

    chart_keywords = [
        'chart', 'graph', 'plot', 'visualize', 'visual',
        'trend', 'compare', 'comparison', 'distribution',
        'over time', 'by month', 'by year', 'by category'
    ]

    q = query.lower()
    for k in chart_keywords:
        if k in q:
            return True

    # Auto-detect numeric 2-column output
    if len(result["columns"]) == 2 and len(result["rows"]) > 1:
        try:
            float(result["rows"][0][1])
            return True
        except:
            pass

    return False


def generate_chart_config(result: dict, query: str):
    """Generate Chart.js configuration from SQL result"""
    columns = result["columns"]
    rows = result["rows"]

    if len(columns) < 2 or not rows:
        return None

    labels = [str(row[0]) for row in rows]

    q = query.lower()
    chart_type = "bar"
    if "line" in q or "trend" in q or "over time" in q:
        chart_type = "line"
    elif "pie" in q:
        chart_type = "pie"

    colors = [
        'rgba(102, 126, 234, 0.8)',
        'rgba(118, 75, 162, 0.8)',
        'rgba(240, 147, 251, 0.8)',
        'rgba(245, 87, 108, 0.8)',
        'rgba(67, 206, 162, 0.8)',
    ]

    datasets = []
    for i in range(1, len(columns)):
        data = []
        for row in rows:
            try:
                data.append(float(row[i]))
            except:
                data.append(0)

        datasets.append({
            'label': columns[i],
            'data': data,
            'backgroundColor': colors[i % len(colors)],
            'borderColor': colors[i % len(colors)].replace("0.8", "1"),
            'borderWidth': 2
        })

    return {
        "type": chart_type,
        "data": {
            "labels": labels,
            "datasets": datasets
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {
                    "display": len(datasets) > 1,
                    "position": "top"
                },
                "title": {"display": False}
            },
            "scales": {
                "y": {"beginAtZero": True}
            } if chart_type != "pie" else {}
        }
    }