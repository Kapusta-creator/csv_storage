# csv_storage
API for csv_storage

Сервис предоставляет возможность хранения, удаления и просмотра csv-файлов. Настроена авторизация,
имеется возможность хранить файлы в публичном или приватном пространстве.

API

<h3>Регистрация пользователя</h3>
endpoint: /api/users<br>
method: POST<br>
Создает нового пользователя и заносит информацию о нем в БД.<br>
Пример использования:<br>
requests.post('http://127.0.0.1:5000/api/users', json={'username': "Kapusta-creator", 'password': 'superpassword'})<br>
Пример ответа сервера:<br>
{"username":"Kapusta-creator"}

<h3>Получение токена для авторизации</h3>
endpoint: /api/token<br>
method: GET<br>
Возвращает уникальный токен для авторизации, используемый при запросах к сервису.<br>
Пример использования:<br>
requests.get("http://127.0.0.1:5000/api/token", auth=("Kapusta-creator", 'superpassword'))<br>
Пример ответа сервера:<br>
{'token': 'eyJpZCI6MX0.ZImXhQ.4iFs4NEC9DS71DiY_PWwE_NQgW0'}<br>
<h3>Загрузка нового файла</h3>
endpoint: /api/upload_file<br>
method: POST<br>
Загружает csv-файл на сервер, в приватную или общую папку.<br>
Пример использования:<br>

file = 'data_res.csv'<br>
files = {<br>
    'json': ('data', json.dumps({'is_private': True, 'delimiter': ","}), 'application/json'),<br>
    'file': (os.path.basename(file), open(file, 'rb'), 'application/octet-stream')<br>
}<br>
requests.post("http://127.0.0.1:5000/api/upload_file", auth=(token, ''), files=files)<br>

Необходимо указать, какой файл вы собираетесь передать, он записывается в словать по ключу 'file' с Content-type равным 'application/octet-stream'.<br>
Также необходимо указать приватный файл или публичный и разделитель данного csv-файла,
эта информация записывается в один словарь с файлом по ключу json с Content-type равным 'application/json'.<br>
Пример ответа сервера:<br>
{'filename': 'data_res.csv', 'username': 'Kapusta-creator'}<br>
<br>

<h3>Удаление файла</h3>
endpoint: /api/delete_file/<filename><br>
method: DELETE<br>
Удаляет файл, загруженный пользователем из приватного или публичного пространства<br>
Пример использования:<br>

requests.delete("http://127.0.0.1:5000/api/delete_file/data_res.csv", auth=(token, ''), json={"from_private": False})<br>

Пример ответа сервера:<br>

{'deleted': 'data_res.csv'}<br>

<h3>Получение списка файлов</h3>
endpoint: /api/file_list<br>
method: GET<br>
Получает список файлов, загруженных данным пользователем или находящихся в публичном пространстве.<br>
Пример использования:<br>

requests.get("http://127.0.0.1:5000/api/file_list", auth=(token, '')<br>

Пример полученных данных:<br>

  {'data': [{'created_date': '2023-06-14T12:49:15Z',<br>
           'delimiter': ",",<br>
           'is_private': False,<br>
           'keys': ['match_id',<br>
                    'team_id',<br>
                    'team_name',<br>
                    'playerId',<br>
                    'x',<br>
                    'y',<br>
                    'shootedBy',<br>
                    'distance',<br>
                    'angle',<br>
                    'passes_before',<br>
                    'shots_before',<br>
                    'shots_by_team_before',<br>
                    'isGoal',<br>
                    'ft_score'],<br>
           'name': 'data_res.csv',<br>
           'user': 'Kapusta-creator'},<br>
          {'created_date': '2023-06-14T12:49:25Z',<br>
           'delimiter': ',',<br>
           'is_private': True,<br>
           'keys': ['match_id',<br>
                    'team_id',<br>
                    'team_name',<br>
                    'playerId',<br>
                    'x',<br>
                    'y',<br>
                    'shootedBy',<br>
                    'distance',<br>
                    'angle',<br>
                    'passes_before',<br>
                    'shots_before',<br>
                    'shots_by_team_before',<br>
                    'isGoal',<br>
                    'ft_score'],<br>
           'name': 'data_res.csv',<br>
           'user': 'Kapusta-creator'}]}<br>

<h3>Просмотр файла</h3>
endpoint: /api/view_file/<filename><br>
method: GET<br>
Получает содержимое файла с возможностью сортировки и фильтрации этого содержимого.<br>
Пример использования:<br>

data = json.dumps({'from_private': True,<br> 'sorting_params': {"values": ["match_id", 'team_id'],<br>
                                                             'ascending': [False, True]},<br>
                    'filter_query': 'x > 10 and shootedBy == "LeftFoot"'})<br>
response = json.loads(requests.get("http://127.0.0.1:5000/api/view_file/data_res.csv", auth=(token, ''), json=data).text)<br>
pprint(response)<br>

Возвращает json, в котором по ключу 'data' лежит конвертированный в json DataFrame, полученный из csv-файла.<br>
Для сортировки необходимо установить sorting_params - {"values": [key1, key2, ...], "ascending": [True/False, True/False, ...]}<br>
Для фильтрации необходимо указать строку filter_query - "{Стандартный Pandas query для фильтрации}"<br>
Пример получаемых данных:<br>

{'data': '{<br>
  "columns": ["match_id","team_id","team_name",...,"shots_by_team_before","isGoal","ft_score"],<br>
  "index":[5619,5620,5621,5625,5638,5647,5635,5636,5642,5646,5649,...,19408,19420,19401,19418,19419],<br>
  "data":[<br>
         [1647846,840,"Spartak Moscow",399974,91.7,72.9,"LeftFoot",17.69475,57.72002,12,0,1,false,"1 : 1"],<br>
         [1647846,840,"Spartak Moscow",404356,69.9,54.2,"LeftFoot",32.66345,4.77675,13,0,2,false,"1 : 1"],<br>
         [1647846,840,"Spartak Moscow",370985,87.6,41.2,"LeftFoot",14.95917,24.14917,12,0,3,false,"1 : 1"],<br>
         [1647846,840,"Spartak Moscow",370985,88.3,41.9,"LeftFoot",14.00766,25.9065,18,1,5,false,"1 : 1"],<br>
         [1647846,840,"Spartak Moscow",364066,87.7,37.6,"LeftFoot",16.26248,32.92785,1,0,0,false,"1 : 1"],<br>
         [1647846,840,"Spartak Moscow",364066,84.6,57.8,"LeftFoot",17.46132,15.81919,8,1,2,false,"1 : 1"],<br>
         [1647846,2059,"Khimki",124605,79.2,57.0,"LeftFoot",22.55793,12.18168,23,0,1,false,"1 : 1"],<br>
         [1647846,2059,"Khimki",433914,80.9,58.2,"LeftFoot",21.69317,14.52309,10,0,2,false,"1 : 1"],<br>
         [1647846,2059,"Khimki",124605,74.0,59.4,"LeftFoot",27.97757,12.63543,36,1,6,false,"1 : 1"],<br>
         [1647846,2059,"Khimki",375411,92.0,50.9,"LeftFoot",8.4,0.0,6,1,10,false,"1 : 1"],<br>
         [1647846,2059,"Khimki",124605,75.9,67.4,"LeftFoot",28.68268,23.76778,42,2,12,false,"1 : 1"]<br>
         ...<br>
         [1293760,4174,"Ural",284399,75.1,40.0,"LeftFoot",27.11646,14.52309,24,1,5,false,"2 : 0"],<br>
         [1293760,7164,"FC Krasnodar",117710,78.6,73.8,"LeftFoot",27.89659,34.10021,7,0,1,false,"2 : 0"],<br>
         [1293760,7164,"FC Krasnodar",117710,69.4,47.8,"LeftFoot",32.61386,3.5862,54,1,1,false,"2 : 0"],<br>
         [1293760,7164,"FC Krasnodar",341315,88.6,52.2,"LeftFoot",12.67318,6.16046,10,0,2,false,"2 : 0"]]<br>
  }'}<br>

