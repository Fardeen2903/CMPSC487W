import datetime
import firebase_admin
from flask import Flask, send_from_directory
from views import views
from firebase_admin import credentials, firestore, storage
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash

app = Flask(__name__)
app.register_blueprint(views, url_prefix="/")
app.secret_key = 'secretsecretsecretkey'

cred = credentials.Certificate("serviceKey.json")
firebase_admin.initialize_app(cred, {'storageBucket': 'w-proj2.appspot.com'})

db = firestore.client()
bucket = storage.bucket()

# Define routes
@app.route('/')
def browse_items():
    items_ref = db.collection('Products')
    items = [doc.to_dict() for doc in items_ref.stream()]
    return render_template('browse.html', items=items)

@app.route('/static/<filename>')
def serve_image(filename):
    return send_from_directory('static', filename)

# Include these lines to serve images stored in Firebase Storage
@app.route('/images/<path:filename>')
def serve_firebase_image(filename):
    return redirect(bucket.blob(filename).generate_signed_url(datetime.timedelta(seconds=3600), method='GET'))

@app.route('/sort')
def sort_items():
    sort_by = request.args.get('sort_by')
    order = request.args.get('order', 'asc')
    items_ref = db.collection('Products').order_by(sort_by)
    items = [doc.to_dict() for doc in items_ref.stream()]
    return render_template('browse.html', items=items)

@app.route('/search')
def search_items():
    search_by = request.args.get('search_by')
    search_term = request.args.get('search_term')
    items_ref = db.collection('Products').where(search_by, '==', search_term)
    items = [doc.to_dict() for doc in items_ref.stream()]
    return render_template('browse.html', items=items)


@app.route('/add', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        name = request.form['Name']
        description = request.form['Description']
        image = request.files['Image']
        ID = request.form['ID']

        if image and 'image' in image.mimetype:
            image_name = f"{ID}.jpg"
            blob = bucket.blob(image_name)
            blob.upload_from_file(image)
            image_url = blob.generate_signed_url(datetime.timedelta(seconds=3600), method='GET')
            db.collection('Products').add({
                'Name': name,
                'Description': description,
                'Image': image_url,
                'ID': ID
            })
            flash('Item added successfully.', 'success')
            return redirect('/')
        else:
            flash('Only image files please.', 'error')
            return redirect('/')
    else:
        return render_template('add.html')


@app.route('/edit/<item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    # Use 'where' query to find the document with the matching 'ID' field
    item_ref = db.collection('Products').where('ID', '==', item_id).stream()

    # Assuming 'ID' is unique, we'll take the first document found
    item = next(item_ref).to_dict()

    if request.method == 'POST':
        name = request.form['Name']
        description = request.form['Description']
        image_url = request.form['Image']
        new_id = request.form['ID']

        # Update the 'Name', 'Description', 'Image', and 'ID' fields
        db.collection('Products').document(item_id).update({
            'Name': name,
            'Description': description,
            'Image': image_url,
            'ID': new_id
        })
        flash('Item updated successfully.', 'success')
        return redirect('/')
    else:
        return render_template('edit.html', item=item)


@app.route('/remove/<item_id>')
def remove_item(item_id):
    # Query Firestore to find the document with the matching 'ID'
    item_ref = db.collection('Products').where('ID', '==', item_id).stream()

    try:
        # Assuming 'ID' is unique, we'll take the first document found
        item_doc = next(item_ref)
        item_doc.reference.delete()
        flash('Item removed successfully.', 'success')
    except StopIteration:
        flash('Item not found or could not be removed.', 'error')

    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, port=8000)