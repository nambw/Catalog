import os
from flask import Flask, render_template, request, redirect,jsonify, url_for, flash
from functools import wraps
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User
from werkzeug import secure_filename

from flask import session as login_session
from flask import send_from_directory
import random, string

from oauth2client import client
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests


#CLIENT_ID = json.loads(
#        open('client_secrets.json', 'r').read())['web']['client_id']
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

UPLOAD_FOLDER = 'images'
ALLOWED_EXTENSIONS = set(['jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DBSession = sessionmaker(bind=engine)
session = DBSession()

#JSON endpoint to get all category
@app.route('/catalog/JSON')
def listCategoryJSON():
    #print "list category jasoned "
    #print category_id
    category = session.query(Category).all()
    return jsonify(eachCategory=[i.serialize for i in category])
    #return jsonify(eachCategory = [category.serialize])

#JSON endpoint to get all items of a category
@app.route('/catalog/<int:category_id>/items/JSON')
def categoryItemJSON(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by( category_id=category_id).all()
    return jsonify(eachItem=[i.serialize for i in items])


#JSON endpoint to get one item detail
@app.route('/catalog/item/<int:item_id>/JSON')
def itemJSON(item_id):
    item = session.query(Item).filter_by(id=item_id).one()
    return jsonify(item=item.serialize)


######## authentication code from udacty course ########  
# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
        for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', lstate = state)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            return redirect(url_for('showLogin', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/gconnect',methods=['POST'])
def gconnect():
  #print request.data
  if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid State'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
  code = request.data
  try:
      oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
      oauth_flow.redirect_uri = 'postmessage'
      credentials = oauth_flow.step2_exchange(code)

  except FlowExchangeError:
      response = make_response(json.dumps('Failed to upgrade the authorization code.'),401)
      response.headers['Content-Type'] = 'application/json'
      return response

  access_token = credentials.access_token
  #print access_token
  url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
  h = httplib2.Http()
  result = json.loads(h.request(url,'GET')[1])

  #print "gconnect credential load done"
  if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')),50)
        response.headers['Content-Type'] = 'application/json'
  #Verify access token is used for intended user
  gplus_id = credentials.id_token['sub']
  if  result['user_id'] != gplus_id:
        #print "gconnect verify token failed to match userid"
        response = make_response(json.dumps("Token USER Id does't match"),401)
        response.headers['Content-Type'] = 'application/json'
        return response

  # Check to se if user already logged in
  stored_credentials = login_session.get('credentials')
  stored_gplus_id = login_session.get('gplusid')
  if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response (json.dumps('Current User is Already logged connect.'),200)
        response.headers['Content-Type'] = 'application/json'

  # store access token for later
  login_session['credentials'] = credentials.to_json()
  login_session['gplusid'] = gplus_id

   # Get User info
  userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
  params = {'access_token': credentials.access_token, 'alt':'json '}
  answer = requests.get(userinfo_url, params=params)
  data = json.loads(answer.text)

  login_session['username'] = data["name"]
  login_session['picture'] = data["picture"]
  login_session['email'] = data["email"]

  # chk if user exists
  user_id =  getUserID(data["email"])
  if  user_id is None:
        user_id = createUser(login_session)
  login_session['user_id'] = user_id

  output = ''
  output += '<h1>Welcome,'
  output += login_session['username']
  output += '!</h1>'
  output += '<img src = " '
  output += login_session['picture']
  output += ' "style = " width:300px; height: 300px; border-radius:150px; -webkit-border-radius:150px; -moz-border-radius:150px;"> '
  flash("You are now logged in as %s"%login_session['username'])
  return output

@app.route("/gdisconnect")
def gdisconnect():
 #disconnect if connected
 credentials = client.OAuth2Credentials.from_json(login_session['credentials'])
 if credentials is None:
   response = make_response(json.dumps('Current user not connected.'), 401)
   response.headers['Content-Type'] = 'application/json'
   return response

 # http GET to revoke token
 access_token = credentials.access_token
 #print access_token
 url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
 h = httplib2.Http()
 result = h.request(url, 'GET')[0]

 #print result
 if result['status'] == '200':
     # reset user session
     del login_session['credentials']
     del login_session['gplusid']
     del login_session['username']
     del login_session['email']
     del login_session['picture']
     del login_session['user_id']
     response = make_response(json.dumps('Success Revoked User '), 200)
     response.headers['Content-Type'] = 'application/json'
     #print (" REVOKE done return")
     return response
 else:
   # error
   #print (" REVOKE FAILED ")
   response = make_response (json.dumps('Failed to revoke token'), 400)
   response.headers['Content-Type'] = 'application/json'
   del login_session['credentials']
   del login_session['gplusid']
   del login_session['username']
   del login_session['email']
   del login_session['picture']
   del login_session['user_id']
   return response


@app.route('/catalog/disconnect')
def disconnect():
   gdisconnect()

   return redirect(url_for('showCategory'))
################### End of Login ###########################


# function for cleaning up during development
@app.route('/catalog/deleteall')
def deleteAll():
    #print 'Deleting all entries'
    clist = session.query(Category).order_by(asc(Category.name)).all()
    for entry in clist:
      items = session.query(Item).filter_by(category_id = entry.id).all()
      for i in items:
	session.delete(items)
      session.delete(entry)
      session.commit()
      flash('%s Successfully Deleted' % entry.name)
    return redirect(url_for('showCategory'))
  
# Lists all categories.. main page 
@app.route('/')
@app.route('/catalog/')
def showCategory():
  #print "Entering Show Category"
  clist = session.query(Category).order_by(asc(Category.name)).all()
  litems = session.query(Item).order_by(desc(Item.created_date)).limit(5)
  itemList = []
  templist = [] 
  if litems != []:
  	#print "latest items"
	for i in litems:
  		templist = [i.name, getCategoryName(i.category_id), i.id]
		#print templist
		itemList.append(templist)
		
  return render_template('category.html', categories = clist, latest_item = itemList)

#Create a new category 
@app.route('/catalog/new/', methods=['GET','POST'])
@login_required
def newCategory():
  if request.method == 'POST':
      newCategory = Category(name = request.form['name'], user_id = login_session['user_id'])
      session.add(newCategory)
      flash('New Category %s Successfully Created' % newCategory.name)
      session.commit()
      return redirect(url_for('showCategory'))
  else:
      return render_template('newCategory.html')

#Edit a Category
@app.route('/catalog/<int:category_id>/edit/', methods = ['GET', 'POST'])
@login_required
def editCategory(category_id):
  editedCategory = session.query(Category).filter_by(id = category_id).one()
  owner = getUserInfo(editedCategory.user_id)
  if (login_session['username'] != owner.name):
        flash('Only Owner can edit Category')
        return redirect(url_for('showCategory'))

  if request.method == 'POST':
      if request.form['name']:
        editedCategory.name = request.form['name']
        flash('Category Successfully Edited %s' % editedCategory.name)
        return redirect(url_for('showCategory'))
  else:
    return render_template('editCategory.html', category = editedCategory)


#Delete a category
@app.route('/catalog/<int:category_id>/delete/', methods = ['GET','POST'])
@login_required
def deleteCategory(category_id):
  categoryToDelete = session.query(Category).filter_by(id = category_id).one()
  owner = getUserInfo(categoryToDelete.user_id)
  if (login_session['username'] != owner.name):
        flash('Only Owner can delete category')
        return redirect(url_for('showCategory'))

  # Check if Category empty before deleting
  items = session.query(Item).filter_by(category_id = category_id).all()
  if (items != []):
	flash('Category must be empty before deleting.')
	return redirect(url_for('showCategory'))
  
  if request.method == 'POST':
    session.delete(categoryToDelete)
    flash('%s Successfully Deleted' % categoryToDelete.name)
    session.commit()
    return redirect(url_for('showCategory', category_id = category_id))
  else:
    return render_template('deleteCategory.html',category = categoryToDelete)

#Show Items in a category
@app.route('/catalog/<int:category_id>/')
@app.route('/catalog/<int:category_id>/item/')
def showItem(category_id):
    clist = session.query(Category).order_by(asc(Category.name)).all()
    try:
       category = session.query(Category).filter_by(id = category_id).one()
       items = session.query(Item).filter_by(category_id = category_id).all()
       owner = getUserInfo(category.user_id)
       return render_template('item.html', items = items, category = category, categories = clist, ownerName = owner.name)
    except:
	flash ('Error in Listing Item ' )
	return redirect(url_for('showCategory'))

#Show Details of Item
@app.route('/catalog/item/<int:item_id>')
@login_required
def showItemDetail(item_id):
    try:
      item = session.query(Item).filter_by(id = item_id).one()
      owner = getUserInfo(item.user_id)
      isOwner = 0
      if login_session['username'] == owner.name:
	isOwner = 1
      return render_template('itemDetail.html', item = item, isOwner = isOwner, category_name = getCategoryName(item.category_id))
    except:
      return None
    

# utility function for image upload
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

# utility function for image upload
@app.route('/catalog/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

#Create a new  item
@app.route('/catalog/<int:category_id>/item/new/',methods=['GET','POST'])
@login_required
def newItem(category_id):
  category = session.query(Category).filter_by(id = category_id).one()
  filename = ""
  if request.method == 'POST':
      file = request.files['photo']
      if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
      newItem = Item(name = request.form['name'], description = request.form['description'], price = request.form['price'], picture = filename, category_id = category_id, user_id = login_session['user_id'])

      session.add(newItem)
      session.commit()
      flash('New item %s  Successfully Created' % (newItem.name))
      return redirect(url_for('showItem', category_id = category_id))
  else:
      return render_template('newItem.html', category_id = category_id)



#Edit an item  
@app.route('/category/<int:category_id>/item/<int:item_id>/edit', methods=['GET','POST'])
@login_required
def editItem(category_id, item_id):
    editedItem = session.query(Item).filter_by(id = item_id).one()
    category = session.query(Category).filter_by(id = category_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        file = request.files['photo']
	#print file.filename
	editedItem.picture = ""
        if file and allowed_file(file.filename):
	    #print "Editing file from form"
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
      	    editedItem.picture  = filename
        session.add(editedItem)
        session.commit()
        flash('Item Successfully Edited')
        return redirect(url_for('showItemDetail', item_id = item_id))
    else:
        return render_template('edititem.html', category_id = category_id, item_id  = item_id, item = editedItem)

#Delete a item
@app.route('/category/<int:category_id>/item/<int:item_id>/delete', methods = ['GET','POST'])
@login_required
def deleteItem(category_id, item_id):
    #category = session.query(Category).filter_by(id = category_id).one()
    itemToDelete = session.query(Item).filter_by(id = item_id).one()
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Item Successfully Deleted')
        return redirect(url_for('showItem', category_id = category_id))
    else:
        return render_template('deleteItem.html', item = itemToDelete)

#utility functions
def getCategoryName(id):
    try:
        category = session.query(Category).filter_by(id=id).one()
        return category.name
    except:
        return None

def getUserInfo(user_id):
    try:
        user = session.query(User).filter_by(id=user_id).one()
        return user
    except:
        return None

def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None



if __name__ == '__main__':
  app.secret_key = 'super_secret_key'
  app.debug = True
  app.run(host = '0.0.0.0', port = 8080)

