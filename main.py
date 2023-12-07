from datetime import datetime
import firebase_admin
from flask import Flask, request, redirect, url_for, render_template, flash
from firebase_admin import credentials, firestore, storage
from werkzeug.utils import secure_filename
import os

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'secretsecretsecretkey'

# Firebase Initialization
cred = credentials.Certificate("ServiceKey.json")
firebase_admin.initialize_app(cred, {'storageBucket': 'cmpsc487w-proj3-34092.appspot.com'})

db = firestore.client()
bucket = storage.bucket()

# Allowed extensions for file uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

# Routes
@app.route('/submit_request', methods=['GET', 'POST'])
def submit_request():
    timestamp = datetime.now()
    if request.method == 'POST':
        request_data = {
            'request_id': request.form['request_id'],
            'apt_num': request.form['apt_num'],
            'issue_area': request.form['issue_area'],
            'issue_description': request.form['issue_description'],
            'request_status': 'pending',
            'time_of_request': timestamp
        }

        file = request.files['photo']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join('path_to_your_upload_folder', filename)
            file.save(file_path)

            # Upload the file to Firebase Storage
            blob = bucket.blob(f'maintenance_requests/{filename}')
            blob.upload_from_filename(file_path)

            # Add the public URL to the request data
            request_data['photo_url'] = blob.public_url

        # Add request data to Firestore
        db.collection('Maintenance Requests').add(request_data)
        flash('Maintenance request submitted successfully.')
        return redirect(url_for('index'))

    return render_template('submit_request.html')

@app.route('/view_requests')
def view_requests():
    # Retrieve filter parameters from the request
    apt_num = request.args.get('apt_num')
    issue_area = request.args.get('issue_area')
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Start with a base query
    query = db.collection('Maintenance Requests')

    # Apply filters based on the presence of query parameters
    if apt_num:
        query = query.where('apt_num', '==', apt_num)
    if issue_area:
        query = query.where('issue_area', '==', issue_area)
    if status:
        query = query.where('request_status', '==', status)
    if start_date:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.where('time_of_request', '>=', start_date_obj)
    if end_date:
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        query = query.where('time_of_request', '<=', end_date_obj)


    requests = query.stream()
    request_list = [{'doc_id': req.id, **req.to_dict()} for req in requests]

    return render_template('view_requests.html', requests=request_list)

@app.route('/update_request/<request_id>', methods=['POST'])
def update_request(request_id):
    db.collection('Maintenance Requests').document(request_id).update({'request_status': 'completed'})
    #flash('Request status updated to completed.')
    return redirect(url_for('view_requests'))

@app.route('/add_tenant', methods=['GET', 'POST'])
def add_tenant():
    if request.method == 'POST':
        tenant_data = {
            'tenant_id': request.form['tenant_id'],       # Changed from 'id'
            'tenant_name': request.form['tenant_name'],   # Changed from 'name'
            'contact_number': request.form['contact_number'], # Changed from 'phone_number'
            'tenant_email': request.form['tenant_email'], # Unchanged
            'apt_num': request.form['apt_num'],           # Unchanged
            'checkin_date': datetime.strptime(request.form['checkin_date'], '%Y-%m-%d') # Changed from 'check_in_date'
        }
        db.collection('Tenants').add(tenant_data)
        flash('Tenant added successfully!')
        return redirect(url_for('manage_tenants'))
    return render_template('add_tenant.html')

@app.route('/edit_tenant/<tenant_id>', methods=['GET', 'POST'])
def edit_tenant(tenant_id):
    tenant_ref = db.collection('Tenants').document(tenant_id)

    if request.method == 'POST':
        updated_data = {
            'tenant_name': request.form['name'],
            'contact_number': request.form['phone_number'],
            'tenant_email': request.form['email'],
            'apt_num': request.form['apartment_number'],
        }
        tenant_ref.update(updated_data)
        flash('Tenant updated successfully!')
        return redirect(url_for('view_tenants'))

    tenant = tenant_ref.get().to_dict()
    return render_template('edit_tenant.html', tenant=tenant, tenant_id=tenant_id)


@app.route('/view_tenants')
def view_tenants():
    tenants = db.collection('Tenants').stream()
    tenant_list = [{'doc_id': tenant.id, **tenant.to_dict()} for tenant in tenants]
    return render_template('view_tenants.html', tenants=tenant_list)


@app.route('/delete_tenant/<tenant_id>', methods=['POST'])
def delete_tenant(tenant_id):
    db.collection('Tenants').document(tenant_id).delete()
    flash('Tenant deleted successfully!')
    return redirect(url_for('view_tenants'))

@app.route('/manage_tenants')
def manage_tenants():
    return render_template('maintain_tenants.html')

if __name__ == '__main__':
    app.run(debug=True, port=8000)