# CaseDS-AI
Case study for the Charles River internship selection process.

## Phase 1
Here, we need to create an interface so that a senior data analyst can enter a ticker and receive a complete report containing: 
- Business summary in 2-3 sentences
- Interpretation of fundamental indicators (not just the numbers, but what they suggest)
- Summary of news classified as positive, negative, or neutral
- Three questions an analyst should investigate before making a decision

To do this, we performed web scraping using yfinance to collect a brief description of the business model and beautiful soup to collect the company's registration and business data from Fundamentus. With the collected data, we set up a prompt for gemini-2.5-flash to generate a strictly standardized report containing the information listed previously.

## Phase 2
At this stage, we want to make the program more robust, without depending so much on the APIs used. To do this, we will incorporate a database containing four tables: one for registration data, one for market data, one to store the generated reports to maintain an accessible history and a final one to store the valid tickers in Fundamentus.

### Pipeline
1. Create an account on [Google AI Studio](https://aistudio.google.com/welcome).
2. Generate an API key and place it in the `.env` file.
3. Run `pip install -r requirements.txt` on your terminal.
4. Run `streamlit run app.py` on your terminal.
   - If it doesn't work, try `python -m streamlit run app.py`.
5. The interface will automatically open in your default web browser and the workflow is highly intuitive:
   - **Generate New Report**: Enter a valid B3 ticker symbol (e.g., `WEGE3`, `PETR4`, `ITUB4`) in the left sidebar and click **Generate Report**. The system will scrape the web, calculate metrics, and generate AI insights in real-time.
   - **View History**: The application automatically saves all generated dashboards to a local SQLite database (`data/equity_research.db`). You can retrieve and view any past snapshot using the **Record** section in the sidebar.
