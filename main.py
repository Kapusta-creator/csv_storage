import json
import os.path

from flask import Flask, request, g
from flask import jsonify
from flask_restful import abort
from flask_httpauth import HTTPBasicAuth
import datetime
import sqlalchemy
import sqlalchemy.orm as orm
from itsdangerous import URLSafeTimedSerializer as Serializer, BadSignature, SignatureExpired
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from db_session import SQLAlchemyBase, create_session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy_serializer import SerializerMixin
import hashlib
import db_session
import pandas as pd

auth = HTTPBasicAuth()
app = Flask(__name__)
app.config["SECRET_KEY"] = 'secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=365)
app.config['ALLOWED_EXTENSIONS'] = ['csv']
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024
app.config['UPLOAD_DIR'] = 'uploads'


class File(SQLAlchemyBase, SerializerMixin):
    __tablename__ = "files"
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    delimiter = sqlalchemy.Column(sqlalchemy.CHAR, default=';')
    is_private = sqlalchemy.Column(sqlalchemy.BOOLEAN, default=False)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    path = sqlalchemy.Column(sqlalchemy.String)
    user = orm.relation('User')

    def __repr__(self):
        return f'File {self.id}: {self.name}'


class User(SQLAlchemyBase, SerializerMixin):
    __tablename__ = "users"
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True, unique=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    files = orm.relation("File", back_populates='user')

    def generate_auth_token(self):
        s = Serializer(app.config['SECRET_KEY'])
        return s.dumps({'id': self.id})

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None
        except BadSignature:
            return None
        session = create_session()
        user = session.query(User).get(data['id'])
        return user

    def __repr__(self):
        return f'User {self.id}: {self.name} '


@auth.verify_password
def verify_password(username_or_token, password):
    session = db_session.create_session()
    user = User.verify_auth_token(username_or_token)
    if not user:
        user = session.query(User).filter_by(name=username_or_token).first()
        if not user or not user.check_password(password):
            return False
    g.user = user
    return True


@app.route('/api/token', methods=['GET'])
@auth.login_required
def get_auth_token():
    token = g.user.generate_auth_token()
    return jsonify({'token': token})


@app.route('/api/users', methods=['POST'])
def new_user():
    if request.method == "POST":
        session = db_session.create_session()
        username = request.json.get('username')
        password = request.json.get('password')
        if username is None or password is None:
            abort(400)
        if session.query(User).filter_by(name=username).first() is not None:
            abort(400)
        user = User(name=username)
        user.set_password(password)
        session.add(user)
        session.commit()
        return jsonify({"username": user.name}), 201
    return jsonify({"status": "Bad request"}), 400


@app.route('/api/upload_file', methods=['POST'])
@auth.login_required
def upload_file():
    if request.method == "POST":
        session = db_session.create_session()
        user = g.user
        data = json.loads(request.files['json'].read().decode('utf_8'))
        file = request.files['file']
        if file.filename.split('.')[-1] not in app.config["ALLOWED_EXTENSIONS"]:
            return jsonify({"status": "bad_request", "reason": "bad file extension"}), 400
        m = hashlib.sha256(bytes(secure_filename(file.filename), 'utf-8')).hexdigest()
        username_hash = hashlib.sha256(bytes(user.name, 'utf-8')).hexdigest()
        if data['is_private']:
            path = os.path.join(app.config['UPLOAD_DIR'], username_hash, m[:2], m[2:4])
        else:
            path = os.path.join(app.config['UPLOAD_DIR'], "public", m[:2], m[2:4])
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        file.save(os.path.join(path, secure_filename(file.filename)))
        file_upload = File(
            name=file.filename,
            delimiter=data['delimiter'],
            created_date=datetime.datetime.now(),
            is_private=data['is_private'],
            path=os.path.join(path, secure_filename(file.filename))
        )
        user.files.append(file_upload)
        session.merge(user)
        session.commit()
        return jsonify({"username": user.name, 'filename': secure_filename(file.filename)}), 201
    abort(400)


@app.route('/api/delete_file/<filename>', methods=['DELETE'])
@auth.login_required
def delete_file(filename):
    if request.method == "DELETE":
        session = db_session.create_session()
        user = g.user
        if request.json['from_private']:
            file = session.query(File).filter(File.name == filename, File.user == user, File.is_private).first()
        else:
            file = session.query(File).filter(File.name == filename, File.user == user, File.is_private == 0).first()
        if file:
            path = file.path
            if os.path.exists(path):
                os.remove(path)
            session.delete(file)
            session.commit()
        else:
            return jsonify({"reason": "There is no such file"}), 404
        return jsonify({"deleted": filename}), 200
    return jsonify({"reason": "Method is not allowed"}), 404


@app.route('/api/file_list', methods=['GET'])
@auth.login_required
def file_list():
    if request.method == 'GET':
        session = db_session.create_session()
        files = session.query(File).filter(or_(File.user == g.user, File.is_private == 0)).all()
        server_files = {'data': []}
        for file in files:
            csv_data = pd.read_csv(file.path, delimiter=file.delimiter)
            keys = csv_data.keys().tolist()
            server_files['data'].append({'delimiter': file.delimiter,
                                         'name': file.name,
                                         'created_date': datetime.datetime.strftime(file.created_date,
                                                                                    "%Y-%m-%dT%H:%M:%SZ"),
                                         'keys': keys,
                                         'is_private': file.is_private,
                                         'user': file.user.name})
        return jsonify(server_files), 200
    return jsonify({"status": "Bad Request"}), 400


@app.route('/api/view_file/<filename>', methods=['GET'])
@auth.login_required
def view_file(filename):
    if request.method == "GET":
        session = db_session.create_session()
        user = g.user
        data = json.loads(request.json)
        if data['from_private']:
            file = session.query(File).filter(File.user == user, File.name == filename, File.is_private).first()
        else:
            file = session.query(File).filter(File.is_private == 0, File.name == filename).first()
        if file:
            csv_data = pd.read_csv(file.path, delimiter=file.delimiter)
            if 'sorting_params' in data:
                sorting_params = data['sorting_params']
            else:
                sorting_params = {}
            if 'filter_query' in data:
                filter_query = data['filter_query']
            else:
                filter_query = ""
            try:
                if sorting_params:
                    csv_data.sort_values(sorting_params['values'], axis=0, ascending=sorting_params['ascending'],
                                         inplace=True)
                if filter_query:
                    csv_data.query(filter_query, inplace=True)
            except KeyError as key_error:
                return jsonify({"status": "Bad Request", "reason": str(key_error)}), 400
            except SyntaxError as syntax_error:
                return jsonify({"status": "Bad Request", "reason": str(syntax_error)}), 400
            except pd.errors.UndefinedVariableError as UndefinedVariableError:
                return jsonify({"status": "Bad Request", "reason": str(UndefinedVariableError)}), 400
            return jsonify({"data": csv_data.to_json(orient='split')}), 200
        else:
            return jsonify({"reason": "There is no such file"}), 404
    return jsonify({"status": "Bad Request"}), 400


def main():
    db_session.global_init('db/file_service.db')
    app.run(port=5000, host='127.0.0.1')


if __name__ == '__main__':
    main()
