import requests
import re
import json
import time
#from loguru import logger
#logger.add('item.log', level='ERROR')


class Session:
    """ Создает сессию и отвечает за запросы к сайту для получения данных. """

    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) \
                    Gecko/20100101 Firefox/84.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,\
                    image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        }

    def __init__(self):
        # инициализация сессии
        session = requests.Session()
        session.headers.update(self.headers)

        self.session = session

    def get(self, url:str) -> str or Bool:
        # выполняет get запрос по ссылке, возвращает html code
        html = self.session.get(url)
        if not html:
            return False
        else:
            return html.text


class ConstructorBase:
    """ Базовый класс для сборки полей. Отвечает за вызов всех методов из Constructor
        и предоставляет вспомогательные методы для получения нужной информации. """

    def construct(self, building_item):
        # сбор всех методов для генерации полей
        method_list = [func for func in dir(self) if callable(getattr(self, func)) and func.startswith('_get')]
        output_data = {}

        # вызов всех методов Constructor
        for method_name in method_list:
            try:
                data = getattr(self, method_name)(building_item)
                output_data = {**data, **output_data}
            except:
                # если произошла ошибка, например для какого-то объекта нет номера дома
                pass

        return output_data

    def _fetch_value_by_regular(self, possible_values:dict, raw_value) -> str:
        # получение ключа как output значения в зависимости от регул. выражения
        for key, reg_value in possible_values.items():
            if re.search(reg_value, raw_value):
                return key


class Constructor(ConstructorBase):
    """ Конструирует все поля. методы _get_property - для генерации каждого поля
        из документации. Аннотациии типов - конечный тип значения из документации,
        а не что возвращает сама функция. (для удобства настройки) """

    def _get_complex(self, building_item) -> str:
        # Название жилого комплекса + регион
        return {'complex':'Достижение (Москва)'}

    def _get_type(self, building_item) -> str:
        # Код типа объекта
        possible_values = {
            'flat':'квартира',
            'apartment':'апартамент',
            'parking':'машиноместо|паркинг',
            'townhouse':'таунхаус|коттедж|дуплекс',
        }
        output = self._fetch_value_by_regular(possible_values, building_item['type'])
        return {'type': output}

    def _get_phase(self, building_item) -> str:
        # Очередь строительства
        return {'phrase':None}

    def _get_building(self, building_item) -> str:
        """ Название корпуса (дома), как на сайте, без слов "корпус", "корп", "блок",
            "строение", знака "№" и т.д. 0 заменять на None. """
        return {'building':None}

    def _get_section(self, building_item) -> str:
        # Название секции, как на сайте, без слова "секция", знака "№" и т.д.
        return {'section':building_item['section']}

    def _get_price_base(self, building_item) -> float:
        """ Стоимость объекта без отделки и без скидок,
            если такая стоимость есть, иначе None. """
        return {'price_base':None}

    def _get_price_finished(self, building_item) -> float:
        """ Стоимость объекта с отделкой и без скидки (с мебелью или без мебели),
            если такая стоимость есть, иначе None. """
        return {'price_finished':float(building_item['real_price'])}


    def _get_price_sale(self, building_item) -> float:
        """ Стоимость без отделки и со скидкой, если такая стоимость есть, иначе None. """
        return {'price_sale':None}

    def _get_price_finished_sale(self, building_item) -> float:
        """ Стоимость с отделкой и со скидкой, если такая стоимость есть, иначе None. """
        return {'price_finished_sale':None}

    def _get_area(self, building_item) -> float:
        """ None если площадь неизвестна или нулевая
            (например, для проданных объектов).  """

        return {'area':float(building_item['sq'])}

    def _get_living_area(self, building_item) -> float:
        """ Жилая площадь. None если площадь неизвестна или нулевая
            (например, для проданных или нежилых объектов). """
        return {'living_area':None}

    def _get_number(self, building_item) -> str:
        """ Номер квартиры (или другого типа объекта) в доме.
            Слова "квартира", "апартамент" и т.п. следует удалить. """
        return {'number':building_item['num']}

    def _get_number_on_site(self, building_item) -> str:
        """ Номер квартиры (или другого типа объекта) на этаже.
            Обычно начинаются с 1 и идут по порядку. Только если указан на сайте.
            Если указано перечисление этажей (“3,6,9,10”), то для каждого этажа
            должна быть одна запись о квартире. Если указан диапазон (“2-5”)
            необходимо уточнить означает ли это что доступны квартиры на 2,3,4,5 этажах
            или это просто указание на то что такие квартиры там есть.  """

        return {'number_on_site':None}

    def _get_rooms(self, building_item) -> int or 'studio':
        """ Для квартир-студий или апартаментов-студий возвращается 'studio',
            иначе число комнат. None как правило у нежилых помещений
            (коммерческих, машиномест и т.д.) и бывает у проданных объектов. """
        return  {'rooms':int(building_item['rooms'])}

    def _get_floor(self, building_item) -> int:
        """ None если этаж неизвестен. """
        return {'floor':int(building_item['floor'])}

    def _get_in_sale(self, building_item) -> int:
        """ Возможны значения 0/1/None. None возвращать если неизвестно,
            это встречается исключительно редко. "Забронирован", "переуступка"
            это в продаже. Объекты без стоимости не в продаже! """
        if building_item['real_price']:
            in_sale = 1
        else:
            in_sale = 0
        return {'in_sale':in_sale}

    def _get_sale_status(self, building_item) -> int:
        """ Текстовое описание статуса квартиры, как на сайте. Например: "в продаже",
            "бронь", "продано". """
        if building_item['reserved'] == 'true':
            sale_status = 'Забронированно'
        else:
            sale_status = None
        return {'sale_status':sale_status}

    def _get_finished(self, building_item) -> int or 'optional':
        """ 1 если объект продаётся только с отделкой (должна быть заполнена
            price_finished и/или price_finished_sale и должны быть пустые price_base
            и price_sale).
            0 если объект продаётся только без отделки (должна быть заполнена
            price_base и/или price_sale, price finished/price_finished_sale
            должны быть пустыми).
            'optional' означает что отделка возможна (могут быть заданы
            price_X в любом сочетании).
        """

        return {'finished':1}

    def _get_currency(self, building_item) -> str:
        """ Устанавливать только если валюта отлична от рублей, например 'USD'. """

        return {}

    def _get_ceil(self, building_item) -> float:
        """ Высота потолка. В метрах, если указана у объекта.
            Если не указана или указана отдельно на сайте - None. """
        return {'ceil':None}

    def _get_article(self, building_item) -> str:
        """ Артикул/название типа объекта/проектный номер, как указано на сайте
            (без знака "№"). Например "18T-2.3-24.9", "17Т-4.2", "23К-4.2-325": """
        return {}

    def _get_finishing_name(self, building_item) -> str:
        """ Название типа/вида отделки, если указан для строки прайс-листа
            или карточки объекта. Если указана отдельно на сайте - не собираем.
            Если указано несколько типов - решаем по ситуации (обратиться к руководителю).
            Если объект без отделки то None. """

        return {'finishing_name':None}

    def _get_furniture(self, building_item) -> int:
        """ Возможные значения 0 (без мебели), 1 (с мебелью или мебель опциональна).
            1 или 0 только если указана у объекта. Если указана отдельно на сайте,
            или неизвестно - None. """
        if re.search('furniture', building_item['scheme_folder']):
            furniture = 1
        else:
            furniture = 0

        return {'furniture':furniture}

    def _get_furniture_price(self, building_item) -> float:
        """ Стоимость меблировки, если она указана. Если меблировки нет
            или стоимость не указана - None или параметр отсутствует. """

        return {'furniture_price':None}

    def _get_plan(self, building_item) -> str:
        """ Абсолютный URL на план объекта. Может быть изображение
            (максимального размера), pdf, word, и т.д., допустим любой формат.
            Приоритет векторным форматам, 2-й приоритет наиболее качественному
            представлению картинки, 3-й приоритет графическим форматам
            (jpg, png, и т.д.).
            Например: https://lidgroup.ru/upload/iblock/ac4/ac45a68ec7946d69e3
                9f0e64a9e00591/77b0bd53b77ebe6dca1ed23317b74fee.jpg """

        if building_item["pdf"]:
            plan = f'https://dom-dostigenie.ru{building_item["pdf"]}'
        else:
            plan = None

        return {'plan':plan}

    def _get_feature(self, building_item) -> [str]:
        """ Как указано на сайте, например: «распашная», «окна на две стороны»,
            «гардеробная комната», «ванная с окном», «с балконом», «видовая»,
            «с камином», «3 с/у», «раздельный с/у», «угловая», «с террасой». """
        features = []
        for feature in building_item['advantages']:
            features.append(feature['name'])

        return features

    def _get_view(self, building_item) -> [str]:
        """ Как указано на сайте, например: [ 'на Москву', 'на реку', 'на рощу' ]. """
        useful_fields = [k for k in building_item if k.startswith('window_view_')]
        views = []
        for useful_field in useful_fields:
            views.append(building_item[useful_field])
        return {'view':views}

    def _get_euro_planning(self, building_item) -> int:
        """ Возможны значения 0/1/None. None возвращать если неизвестно.
            Значение может быть закодировано, например, в типе ("евро-студия"),
            или количестве комнат ("2Е"). """
        return {'euro_planning':None}

    def _get_sale(self, building_item) -> [str]:
        """ Как указано для объекта, например: "кухня в подарок",
            "скидка при 100% оплате". Собирать только если относятся к объекту.
            Если относятся ко всему ЖК - не собирать, None. """
        return {'sale':None}

    def _get_discount_percent(self, building_item) -> float or int:
        """ Размер скидки в процентах, как она указана на сайте.
            Только если явно указан процент скидки, например: "скидка 2%".
            Рассчитывать в парсере не надо! """
        return {}

    def _get_discount(self, building_item) -> float:
        """ Размер скидки в валюте, как она указана на сайте. Только если
            для объекта явно указан размер скидки, например: "скидка: 300 т.р.".
            Рассчитывать в парсере не надо! """
        return {}

    def _get_comment(self, building_item) -> str:
        """ Если комментарий не нужен, ключ можно не указывать."""

        return {}

class Formatter:
    """ Приводит данные к нужному формату. """

    def __init__(self):
        # экземпляр конструктора
        self.constructor_ins = Constructor()

    def format(self, responce_html:str) -> list:
        # для вннешнего запуска общего процесса форматирования
        responce_json = self._convert_to_json(responce_html)
        # все объекты недвижимости из запроса, со свойствами
        items = responce_json['data']
        if not items:
            return False

        output_datas = []
        for item in items:
            output_datas.append(self.constructor_ins.construct(item))

        return output_datas

    def _convert_to_json(self, html:str) -> json:
        # преобразует сырой html в json
        return json.loads(html.strip())


class Parse:
    """ Собирает данные и выводит окончательный результат. """

    # ссылка пагинации
    url = 'https://dom-dostigenie.ru/ajax/flats/?page={page}&cnt=60&filter\
        [project]=jazz&filter[special]=&filter[type]=&filter[fav]=0&sort[sec]=\
        0&sort[name]=0&sort[sq]=0&sort[price]=2&sort[rooms]=0&sort[floor]=0'
    # задержка при парсинге
    timeout_sec = 5

    def __init__(self):
        self.session_ins = Session()
        self.formatter_ins = Formatter()


    def run(self):
        """ Старт процесса парсинга """
        # конечный лист со всеми значениями объектов(квартир и пр)
        output_all = []
        for page in range(1, 1000):
            html = self.session_ins.get(self.url.format(page=page))

            output_items = self.formatter_ins.format(html)
            # если пагинация закончилась
            if not output_items:
                break

            output_all += output_items

            time.sleep(self.timeout_sec)

        print(json.dumps(output_all))

if __name__ == '__main__':
    Parse().run()
