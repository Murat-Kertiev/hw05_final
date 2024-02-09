# Yatube
____
###### Блог Yatube, в котором реализованы следующие возможности:
+ _создание постов, с выбором подходящей группы и их последующее редактирование (CRUD) автором поста_
+ _добавление и редактирование комментариев к постам_
+ _возможность подписки/отписки на(от) автора_

### Как запустить проект:
____

Клонировать репозиторий и перейти в него в командной строке:

```
git clone git@github.com:Murat-Kertiev/hw05_final.git
```

```
cd hw05_final
```

Cоздать и активировать виртуальное окружение:

```
python -m venv venv
```

```
source venv/Scripts/activate
```

```
python -m pip install --upgrade pip
```

Установить зависимости из файла requirements.txt:

```
pip install -r requirements.txt
```

Выполнить миграции:

```
cd yatube/
python manage.py migrate
```

Запустить проект:

```
python manage.py runserver
```
