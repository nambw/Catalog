Project Item Catalog :-
This provides a web app for listing items. It can be used as a neighborhood backyard sale where residents can login and add categories and items them want to sell and look for items that are on sale. This app can be extended to have the online buying option like checkout cart etc.
For now it only has edit/delete and listing features.
Authentcation is provided by  google plus.Authentication code is taken from the Udacity Authentcation course.
Other third party authentication like facebook can be added easily.
Images of items are uploaded and stored in directory images currently. The app can be extended to use thirdparty cloud storage.

Note: Current code works with flask version 0.9  
Oauth2 credential has a known bug with later version of flask and gives a TypeError with JSON serialization.
Use command "pip install flask == 0.9" to install the version 0.9 of flask.

Files included :
   project.py  -    The main file tp start the web app   
   database_setup.py - This is used to create the catalog database
   templates/*.html    HTML files for all web routes 
   images/*            Directory to store uploaded images
   static/*            CSS files for the app

Libraries Used:
    os httplib2 json requests
    from flask: make_response Flask, render_template, request, redirect,jsonify, url_for, flash send_from_directory

    from sqlalchemy: create_engine, asc, desc
    from werkzeug : secure_filename
    from oauth2client.client: flow_from_clientsecrets FlowExchangeError

How to use:
First setup empty database by running "python database_setup.py"
Then Invoke the web app by running "python project.py"
Main Page: http://localhost:8080/catalog/

Click on Login to Add/Delete/Edit Category and Add/Delete/Edit Items in a category
A category can be deleted only if its empty. So items must be deleted first before deleting Category
A Category or an Item can only be edited or deleted by the owner.

The Catalog is available for browsing only wihtout Login. No Edit/Add/Delete option is available without Login

Available JSON Endpoint APIs:
http://localhost:8080/catalog/JSON                        All category
http://localhost:8080/catalog/<category_id>/items/JSON    All items
http://localhost:8080/catalog/item/<item_id>/JSON    Single item





