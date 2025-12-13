# ISATRecruiter 
- A tool that helps prospective and current students find their way in the ISAT program
- Built using AI & RAG to create ISAT-advisor style responses to questions augmented with information from ISAT resources (course catalog and ISAT website)
- Runs locally from a Vercel Server
- Uses OpenAI 4o (REQUIRES A KEY)


  # Setup
  run requirements.txt
  <br>
  By running:
  `pip install -r requirements.txt`

  # Dependencies
  python version: 3.11 


  # To create a virtual environment
  Run the following commands in terminal"
  <br>
  `python3 -m venv [name of envirnoment]`
  <br>
  `source [name of environment]/bin/activate`
  <br>
  **To activate:**
  <br>
  `source /Users/[your-path]/[your environment]/bin/activate`


  # To run Local development server with Vercel
  NOTE: only works if ran from Frontend
  <br>
  `cd Frontend `
  <br>
  `npm run dev`



  # .env
  Create a .env file and add your openAI key, starts with sk-...
  <br>
  `OPENAI_API_KEY=sk-`

DR. TEATE'S KEY:

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

  <br>
  LangSmith Key, starts with lsv...
  <br>
  `LANGSMITH_API_KEY=lsv`
  <br>
  If using LangSmith add your
  <br>
  `LANGSMITH_WORKSPACE_ID`

