HOW TO START

A. IMPORTANT! GUMAWA ng virtual environment. Steps:
   1. create venv -> python -m venv LIPMIC_webapp
   2. activate venv -> Desktop\LIPMIC_webapp\Scripts\activate
   3. change directory -> cd Desktop\LIPMIC_webapp

B. Install python packages:
        -> pip install -r requirements.txt

C. To run the server
        -> Go to command prompt
        -> flask --app board\__init__.py run --host=0.0.0.0 --port=8080 --debug

[Optional] Para hindi mag run yung lip-reading model punta ka sa pages.py at comment out mo yung line 2.
