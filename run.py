from app import create_app

app = create_app()

if __name__ == "__main__":
    print("\n  FinTrack → http://localhost:5000\n")
    print("  Auth:         POST /api/signup  POST /api/login  GET /logout")
    print("  Dashboard:    GET  /api/balance  /api/summary  /api/categories  /api/insights")
    print("  Transactions: GET|POST /api/transactions  DELETE /api/transactions/<id>")
    print("  Analytics:    GET /api/analytics?year=&month=")
    print("  Forecast:     GET /api/forecast?days=30")
    print("  Budgets:      GET|POST /api/budgets")
    print("  Recs:         GET /api/recommendations")
    print("  CSV:          POST /api/upload-csv\n")
    app.run(debug=True, port=5000)
