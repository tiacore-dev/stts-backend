from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Response, jsonify
import os
import logging
# Получаем логгер по его имени
logger = logging.getLogger('chatbot')

audio_bp = Blueprint('audio', __name__)


# Загрузка аудиофайла
@audio_bp.route('/audio/upload', methods=['POST'])
@jwt_required()
def upload_audio():
    from app.database.managers.audio_manager import AudioFileManager
    from app.s3 import get_s3_manager, get_bucket_name

    db = AudioFileManager()
    s3_manager = get_s3_manager()
    bucket_name = get_bucket_name()
    current_user = get_jwt_identity()
    logger.info(f"Пользователь {current_user} пытается загрузить аудиофайл.", extra={'user_id': current_user['login']})

    file = request.files.get('file')
    
    if not file:
        logger.error(f"Пользователь {current_user} не выбрал файл для загрузки.", extra={'user_id': current_user['login']})
        return jsonify({'error': 'No file provided'}), 400

    file_name_input = request.form.get('fileName')  # Имя файла от пользователя
    file_extension = os.path.splitext(file.filename)[1]  # Получаем расширение файла
    # Генерируем полное имя файла с расширением
    full_file_name = f"{file_name_input}{file_extension}"

    # Заменяем пробелы на нижние подчеркивания для s3_key
    s3_key = full_file_name.replace(' ', '_')

    file_size = file.content_length  # Получаем размер файла напрямую
    logger.info(f"Файл для загрузки: {full_file_name} (размер: {file_size} байт)", extra={'user_id': current_user['login']})

    try:
        logger.info(f'Попытка загрузки аудио в бакет: {bucket_name}', extra={'user_id': current_user['login']})

        # Загрузка файла в S3 напрямую из объекта файла
        s3_manager.upload_fileobj(file, bucket_name, s3_key)  # Используем s3_key с нижними подчеркиваниями
        audio_id = db.add_audio_file(current_user['user_id'], file_name_input, file_extension, file_size, bucket_name, s3_key)  # Сохраняем данные в БД
        logger.info(f"Файл {full_file_name} успешно загружен в S3.", extra={'user_id': current_user['login']})

        return jsonify({'message': 'File uploaded successfully', 'audio_id': audio_id}), 200
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}", extra={'user_id': current_user['login']})
        return jsonify({'error': 'File upload failed'}), 500




# Получение списка файлов с пагинацией
@audio_bp.route('/audio/all', methods=['GET'])
@jwt_required()
def get_files():
    from app.database.managers.audio_manager import AudioFileManager
    
    db = AudioFileManager()
    current_user = get_jwt_identity()
    logger.info(f"Пользователь {current_user} запрашивает список файлов.", extra={'user_id': current_user['login']})

    page = int(request.args.get('page', 1))
    per_page = 10

    try:
        # Получаем файлы для текущего пользователя
        files = db.get_audio_files_by_user(current_user['user_id'])
        total_files = len(files)
        total_pages = (total_files + per_page - 1) // per_page
        
        # Пагинация
        files_paginated = files[(page - 1) * per_page: page * per_page]
        
        file_data = [
            {
                'name': f[0],  # file_name
                's3_key': f[1],  # s3_key
                'bucket_name': f[2]  # bucket_name
            }
            for f in files_paginated
        ]

        logger.info(f"Отправлен список файлов для страницы {page}.", extra={'user_id': current_user['login']})
        return jsonify({'files': file_data, 'total_pages': total_pages}), 200
    except Exception as e:
        logger.error(f"Ошибка при получении списка файлов: {e}", extra={'user_id': current_user['login']})
        return jsonify({'error': 'Failed to retrieve files'}), 500



# Удаление файла
@audio_bp.route('/audio/<audio_id>/delete', methods=['DELETE'])
@jwt_required()
def delete_file(audio_id):
    from app.database.managers.audio_manager import AudioFileManager
    db = AudioFileManager()
    from app.s3 import get_s3_manager, get_bucket_name
    current_user = get_jwt_identity()
    

    if not audio_id:
        return jsonify({'error': 'No file name provided'}), 400

    s3_manager = get_s3_manager()
    bucket_name = get_bucket_name()

    # Проверяем, что файл принадлежит текущему пользователю
    file_record = db.get_audio_file_by_id(current_user['user_id'], audio_id)
    if not file_record:
        return jsonify({'error': 'File not found or access denied'}), 404

    try:
        # Удаляем файл из S3
        s3_manager.delete_file(bucket_name, file_record.s3_key)
        audio_id=file_record.audio_id
        db.delete_audio_file(audio_id)  # Метод для удаления записи из базы
        logger.info(f"Файл {audio_id} успешно удален.", extra={'user_id': current_user['login']})
        return jsonify({'message': 'File deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Ошибка при удалении файла: {e}", extra={'user_id': current_user['login']})
        return jsonify({'error': 'File deletion failed'}), 500


@audio_bp.route('/audio/<audio_id>/download', methods=['GET'])
@jwt_required()
def download_file_bytes():
    from app.database.managers.audio_manager import AudioFileManager
    db = AudioFileManager()
    from app.s3 import get_s3_manager, get_bucket_name
    current_user = get_jwt_identity()
    audio_id = request.args.get('audio_id')

    logger.info(f"Получен запрос на скачивание файла: {audio_id} для пользователя: {current_user}", extra={'user_id': current_user['login']})

    if not audio_id:
        logger.warning("Имя файла не указано.", extra={'user_id': current_user['login']})
        return jsonify({'error': 'No file name provided'}), 400

    s3_manager = get_s3_manager()
    bucket_name = get_bucket_name()

    # Проверяем, что файл принадлежит текущему пользователю
    file_record = db.get_audio_file_by_id(current_user['user_id'], audio_id)
    if not file_record:
        logger.warning(f"Файл '{audio_id}' не найден или доступ запрещен для пользователя '{current_user}'.", extra={'user_id': current_user['login']})
        return jsonify({'error': 'File not found or access denied'}), 404

    try:
        # Получаем файл из S3
        audio_bytes = s3_manager.get_file(bucket_name, file_record.s3_key)
        if audio_bytes is None:
            logger.error(f"Не удалось получить содержимое файла '{audio_id}' из S3.", extra={'user_id': current_user['login']})
            return jsonify({'error': 'Could not retrieve audio file'}), 500
        
        return Response(audio_bytes, mimetype='audio/mpeg')  # Укажите корректный тип контента
    except Exception as e:
        logger.error(f"Ошибка при получении аудиофайла '{audio_id}' из S3: {str(e)}", extra={'user_id': current_user['login']})
        return jsonify({'error': f'Could not retrieve audio file: {str(e)}'}), 500


@audio_bp.route('/audio/<audio_id>/download_url', methods=['GET'])
@jwt_required()
def download_file(audio_id):
    from app.database.managers.audio_manager import AudioFileManager
    db = AudioFileManager()
    from app.s3 import get_s3_manager, get_bucket_name
    current_user = get_jwt_identity()
    audio_id = request.args.get('audio_id')

    if not audio_id:
        return jsonify({'error': 'No file name provided'}), 400

    s3_manager = get_s3_manager()
    bucket_name = get_bucket_name()

    file_record = db.get_audio_file_by_id(current_user['user_id'], audio_id)
    if not file_record:
        return jsonify({'error': 'File not found or access denied'}), 404

    # Генерируем временный URL для скачивания файла
    url = s3_manager.generate_presigned_url(bucket_name, file_record.s3_key)

    if url:
        return jsonify({'url': url}), 200
    else:
        return jsonify({'error': 'Could not generate download URL'}), 500

