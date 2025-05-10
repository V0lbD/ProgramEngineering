import time
import random
import threading
from queue import Queue


# паттерн Состояние для настройки принтера
class PrinterState:
    def configure(self, printer):
        pass

    def print_doc(self, content, printer):
        pass


class A4State(PrinterState):
    def configure(self, printer):
        print(f"{printer.name}: Настройка для печати A4")
        time.sleep(1)

    def print_doc(self, content, printer):
        print(f"{printer.name}: Печать A4 документа: {content}")
        time.sleep(2)


class PhotoState(PrinterState):
    def configure(self, printer):
        print(f"{printer.name}: Настройка для печати фотографий")
        time.sleep(1)

    def print_doc(self, content, printer):
        print(f"{printer.name}: Печать фотографии: {content}")
        time.sleep(3)


class Printer:
    def __init__(self, name):
        self.name = name
        self.state = random.choice([A4State(), PhotoState()])
        self.lock = threading.Lock()

    def set_state(self, state):
        with self.lock:
            self.state = state

    def configure(self):
        with self.lock:
            self.state.configure(self)

    def print_document(self, content):
        with self.lock:
            self.state.print_doc(content, self)


# цепочка обязанностей для обработки запросов
class PrinterHandler:
    def __init__(self, successor=None):
        self.successor = successor

    def handle_request(self, request):
        if self.can_handle(request):
            self.process_request(request)
        elif self.successor:
            self.successor.handle_request(request)
        else:
            print(f"Запрос не может быть обработан: {request}")

    def can_handle(self, request):
        pass

    def process_request(self, request):
        pass


class BlackAndWhiteHandler(PrinterHandler):
    def __init__(self, printer, successor=None):
        super().__init__(successor)
        self.printer = printer

    def can_handle(self, request):
        return not request['needs_color']

    def process_request(self, request):
        print(f"\nЧ/Б принтер {self.printer.name} начинает обработку запроса {request['id']}:")
        self.printer.set_state(A4State() if request['type'] == 'A4' else PhotoState())
        self.printer.configure()
        self.printer.print_document(request['content'])


class ColorHandler(PrinterHandler):
    def __init__(self, printer, successor=None):
        super().__init__(successor)
        self.printer = printer

    def can_handle(self, request):
        return request['needs_color']

    def process_request(self, request):
        print(f"\nЦветной принтер {self.printer.name} начинает обработку запроса {request['id']}:")
        self.printer.set_state(A4State() if request['type'] == 'A4' else PhotoState())
        self.printer.configure()
        self.printer.print_document(request['content'])


# паттерн Заместитель для фотографий
class PhotoService:
    def take_photo(self):
        pass


class RealPhotoService(PhotoService):
    def take_photo(self):
        print("Сервис фотографирования: создание фотографии...")
        time.sleep(2)
        return f"Фото-{random.randint(1, 100)}"


class PhotoServiceProxy(PhotoService):
    def __init__(self):
        self.real_service = RealPhotoService()
        self.cached_photo = None
        self.lock = threading.Lock()

    def take_photo(self):
        with self.lock:
            if not self.cached_photo:
                print("Прокси: запрос на создание новой фотографии...")
                self.cached_photo = self.real_service.take_photo()
            else:
                print("Прокси: использование сохраненной фотографии")
            return self.cached_photo


# генератор случайных запросов
def generate_request(request_id):
    doc_type = random.choice(['A4', 'photo'])
    needs_color = random.choice([True, False]) if doc_type == 'A4' else True
    has_photo = random.choice([True, False]) if doc_type == 'photo' else False
    return {
        'id': request_id,
        'type': doc_type,
        'needs_color': needs_color,
        'has_photo': has_photo,
        'content': None
    }


# обработчик запросов
def request_processor(handler, photo_proxy, request_queue):
    while True:
        request = request_queue.get()
        if request is None:  # сигнал завершения
            break

        print(f"\n{'=' * 40}\nПолучен запрос {request['id']}:")
        print(f"Тип: {request['type']}, Цвет: {request['needs_color']}, Фото: {request['has_photo']}")

        if request['type'] == 'photo' and not request['has_photo']:
            request['content'] = photo_proxy.take_photo()
        else:
            request['content'] = f"Документ-{request['id']}"

        handler.handle_request(request)
        request_queue.task_done()


def main():
    # инициализация компонентов
    bw_printer = Printer("Ч/Б-Принтер-1")
    color_printer = Printer("Цветной-Принтер-1")
    color_handler = ColorHandler(color_printer)
    bw_handler = BlackAndWhiteHandler(bw_printer, color_handler)
    photo_proxy = PhotoServiceProxy()

    # очередь для запросов
    request_queue = Queue()

    # создаем и запускаем обработчики запросов
    num_workers = 3
    workers = []
    for _ in range(num_workers):
        worker = threading.Thread(
            target=request_processor,
            args=(bw_handler, photo_proxy, request_queue)
        )
        worker.start()
        workers.append(worker)

    # генерация случайных запросов в случайное время
    for i in range(1, 6):
        time.sleep(random.uniform(0.5, 2.0))  # имитация нерегулярного поступления запросов
        request = generate_request(i)
        print(f"\nПользователь отправил запрос {i} в {time.strftime('%H:%M:%S')}")
        request_queue.put(request)

    # ожидание завершения всех задач
    request_queue.join()

    # остановка рабочих потоков
    for _ in range(num_workers):
        request_queue.put(None)
    for worker in workers:
        worker.join()


if __name__ == "__main__":
    main()