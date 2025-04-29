HOW TO START

1. IMPORTANT! GUMAWA ng virtual environment. Steps:
        create venv -> python -m venv LIPMIC_webapp
        activate venv -> Desktop\LIPMIC_webapp\Scripts\activate
        change directory -> cd Desktop\LIPMIC_webapp

2. Install python packages:
        -> pip install -r requirements.txt

3. To run the server
        -> Go to command prompt
        -> flask --app board\__init__.py run --host=0.0.0.0 --port=8080 --debug

[Optional] Para hindi mag run yung lip-reading model punta ka sa pages.py at comment out mo yung line 2.
        1 ...
        2 from board import app <- comment mo ito para ma run pa din yung flask web app ng walang tensorflow running sa bg!
        3
