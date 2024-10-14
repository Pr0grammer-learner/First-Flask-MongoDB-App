from flask import Flask, render_template, request, redirect, url_for, abort
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

# Подключение к MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['notes_app']

# Коллекции в базе данных
users_collection = db['users']
notes_collection = db['notes']
tags_collection = db['tags']

# Создание индекска для поиска
notes_collection.create_index([("title", "text"), ("content", "text")], name="title_text_content_text")
# Создание индекса для поиска по тегам
tags_collection.create_index([("name", "text")], name="name_text")

def get_all_notes():
    # Извлекаем все заметки из коллекции notes
    notes = list(db.notes.find())
    return notes

# Функция для получения пользователя по ID
def get_user_by_id(user_id):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    return user

# Главная страница
@app.route('/')
def index():
    # Получение списка всех заметок
    all_notes = notes_collection.find()
    return render_template('index.html', notes=all_notes)

# Страница просмотра всех тегов
@app.route('/tags')
def tags():
    all_tags = db.tags.find()
    return render_template('tags.html', tags=all_tags)

# Страница просмотра всех заметок
@app.route('/notes')
def notes():
    # Получаем список заметок из базы данных
    all_notes = get_all_notes()

    return render_template('notes.html', notes=all_notes,  get_user_by_id=get_user_by_id)

# Страница просмотра всех пользователей
@app.route('/users')
def users():
    # Используем агрегацию для объединения пользователей и их заметок
    pipeline = [
        {
            '$lookup': {
                'from': 'notes',
                'localField': '_id',
                'foreignField': 'user_id',
                'as': 'user_notes'
            }
        }
    ]

    # Получаем список всех пользователей с их заметками
    all_users = list(users_collection.aggregate(pipeline))

    return render_template('users.html', users=all_users)

# Страница просмотра отдельной заметки
@app.route('/note/<note_id>')
def view_note(note_id):
    # Получение информации о заметке по ее идентификатору
    note = notes_collection.find_one({'_id': ObjectId(note_id)})
    return render_template('view_note.html', note=note,  get_user_by_id=get_user_by_id)

# Добавление новой заметки
@app.route('/add_note', methods=['GET', 'POST'])
def add_note():
    if request.method == 'POST':
        # Получение данных из формы POST запроса
        title = request.form.get('title')
        content = request.form.get('content')
        user_id = ObjectId(request.form.get('user'))  # Преобразование user_id в ObjectId
        tags = request.form.getlist('tags')  # Используйте getlist для получения списка значений

        # Пример: Добавление заметки в коллекцию
        notes_collection.insert_one({
            'title': title,
            'content': content,
            'user_id': user_id,  # Используем 'user_id' вместо 'tags' для представления пользователя
            'tags': tags
        })

        # После добавления заметки перенаправляем пользователя на главную страницу
        return redirect(url_for('index'))

    # Если запрос GET, отображаем форму для добавления новой заметки
    all_users = db.users.find()  # Получаем всех пользователей из базы данных
    all_tags = db.tags.find()  # Получаем все теги из базы данных
    return render_template('add_note.html', users=all_users, tags=all_tags)  # Передаем пользователей и теги в шаблон


# Редактирование заметки
@app.route('/edit_note/<note_id>', methods=['GET', 'POST'])
def edit_note(note_id):
    # Получение информации о заметке по ее идентификатору
    note = notes_collection.find_one({'_id': ObjectId(note_id)})
    all_tags = tags_collection.find()
    all_users = users_collection.find()

    # Получение информации о пользователе
    user_id = note.get('user_id')
    user = get_user_by_id(user_id)

    if request.method == 'POST':
        # Обновление данных заметки
        title = request.form.get('title')
        content = request.form.get('content')
        selected_tags_ids = request.form.getlist('tags')
        selected_user_id = ObjectId(request.form.get('user'))  # Преобразование user_id в ObjectId

        # Пример: Обновление данных заметки в коллекции
        notes_collection.update_one(
            {'_id': ObjectId(note_id)},
            {'$set': {
                'title': title,
                'content': content,
                'tags': selected_tags_ids,
                'user_id': selected_user_id
            }}
        )

        # После редактирования заметки перенаправляем пользователя на страницу просмотра заметки
        return redirect(url_for('view_note', note_id=note_id))

    # Если запрос GET, отображаем форму редактирования
    return render_template('edit_note.html', note=note, user=user, tags=all_tags, users=all_users)

# Удаление заметки
@app.route('/delete_note/<note_id>')
def delete_note(note_id):
    # Удаление заметки из коллекции
    notes_collection.delete_one({'_id': ObjectId(note_id)})
    return redirect(url_for('index'))

# Маршруты для пользователей
@app.route('/users/add', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        # Получение данных из формы
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')  

        # Вставка нового пользователя в базу данных
        user_data = {'username': username, 'email': email, 'password': password}
        result = db.users.insert_one(user_data)

        if result.inserted_id:
            # Пользователь успешно добавлен
            return redirect(url_for('users'))

    return render_template('add_user.html')

@app.route('/users/<user_id>')
def view_user(user_id):
    # Получение пользователя по ID
    user = db.users.find_one({'_id': ObjectId(user_id)})

    # Получение заметок пользователя
    user_notes = db.notes.find({'user_id': ObjectId(user_id)})

    return render_template('view_user.html', user=user, user_notes=user_notes)

@app.route('/users/<user_id>/edit', methods=['GET', 'POST'])
def edit_user(user_id):
    user = db.users.find_one({'_id': ObjectId(user_id)})

    # Получение всех заметок для данного пользователя
    user_notes = list(db.notes.find({'user_id': ObjectId(user_id)}))

    if request.method == 'POST':
        # Обработка формы редактирования пользователя
        new_username = request.form.get('username')
        new_email = request.form.get('email')

        # Обновление данных пользователя в базе данных
        db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'username': new_username, 'email': new_email}})

        # Перенаправление с параметром user_notes
        return redirect(url_for('view_user', user_id=user_id, user_notes=user_notes))

    return render_template('edit_user.html', user=user, user_notes=user_notes)

@app.route('/users/<user_id>/delete')
def delete_user(user_id):
    # Удаление пользователя
    user = db.users.find_one({'_id': ObjectId(user_id)})

    if user:
        # Удаление заметок пользователя
        db.notes.delete_many({'user_id': user['_id']})

        # Удаление пользователя
        db.users.delete_one({'_id': ObjectId(user_id)})

        return redirect(url_for('users'))
    else:
        abort(404)  # Или любой другой код состояния, указывающий на отсутствие ресурса

# Маршруты для тегов
@app.route('/tags/add', methods=['GET', 'POST'])
def add_tag():
    if request.method == 'POST':
        # Получение данных из формы POST запроса
        tag_name = request.form.get('tag_name')

        # Пример: Добавление тега в коллекцию
        tags_collection.insert_one({'name': tag_name})

        # После добавления тега перенаправляем пользователя на страницу с тегами
        return redirect(url_for('tags'))

    # Если запрос GET, отображаем форму для добавления нового тега
    return render_template('add_tag.html')

@app.route('/tags/<tag_id>')
def view_tag(tag_id):
    # Получение информации о теге по его идентификатору
    tag = tags_collection.find_one({'_id': ObjectId(tag_id)})
    return render_template('view_tag.html', tag=tag)

@app.route('/tags/<tag_id>/edit', methods=['GET', 'POST'])
def edit_tag(tag_id):
    # Получение информации о теге по его идентификатору
    tag = tags_collection.find_one({'_id': ObjectId(tag_id)})

    if request.method == 'POST':
        # Обновление данных тега
        new_tag_name = request.form.get('tag_name')

        # Пример: Обновление данных тега в коллекции
        tags_collection.update_one(
            {'_id': ObjectId(tag_id)},
            {'$set': {'name': new_tag_name}}
        )

        # После редактирования тега перенаправляем пользователя на страницу просмотра тега
        return redirect(url_for('view_tag', tag_id=tag_id))

    # Если запрос GET, отображаем форму редактирования
    return render_template('edit_tag.html', tag=tag)

@app.route('/tags/<tag_id>/delete')
def delete_tag(tag_id):
    # Удаление тега из коллекции
    tags_collection.delete_one({'_id': ObjectId(tag_id)})
    return redirect(url_for('tags'))

# Обновление типа данных user_id в коллекции notes
@app.route('/update_user_ids')
def update_user_ids():
    all_notes = notes_collection.find()

    for note in all_notes:
        user_id_str = note.get('user_id')
        user_id_obj = ObjectId(user_id_str)
        
        notes_collection.update_one(
            {'_id': note['_id']},
            {'$set': {'user_id': user_id_obj}}
        )

    return "User IDs updated successfully!"

# Добавление маршрута для поиска
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_query = request.form.get('search_query')

        # Поиск по тексту заметок (поля "title" и "content")
        text_search_results = notes_collection.find({"$text": {"$search": search_query}})

        # Поиск по тегам
        tag_search_results = notes_collection.find({"tags": {"$in": [search_query]}})

        # Объединение результатов поиска
        results = list(text_search_results) + list(tag_search_results)

        return render_template('search_results.html', results=results, query=search_query)

    return render_template('search.html')

if __name__ == '__main__':
    app.run(debug=True)