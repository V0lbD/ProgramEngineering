import sys
from datetime import *
import json
import math
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Set
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QListWidget, QMessageBox,
                             QSpinBox, QComboBox, QAction, QFileDialog, QGraphicsView,
                             QGraphicsScene, QGraphicsEllipseItem, QGraphicsTextItem,
                             QGraphicsLineItem, QGraphicsItem)
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QColor, QPen, QPainter
import traceback
import sys
from PyQt5.QtCore import QObject, pyqtSlot


def exception_hook(exctype, value, tb):
    """Перехватывает все исключения"""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    print(f"Critical error: {error_msg}")
    QMessageBox.critical(None, "Ошибка", f"Произошла критическая ошибка:\n{str(value)}")
    sys.__excepthook__(exctype, value, tb)


sys.excepthook = exception_hook


# region Модель данных
class CityMap:
    """Класс для хранения карты городов и дорог с поддержкой множественных дорог"""

    def __init__(self):
        self.cities: Dict[str, Dict[str, List[int]]] = {}  # {city: {neighbor: [cost1, cost2]}}

    def add_city(self, name: str) -> bool:
        """Добавить город с уникальным именем"""
        if name in self.cities:
            return False
        self.cities[name] = {}
        return True

    def remove_city(self, name: str) -> bool:
        """Удалить город и все связанные с ним дороги"""
        if name not in self.cities:
            return False

        for city in self.cities:
            if name in self.cities[city]:
                del self.cities[city][name]

        del self.cities[name]
        return True

    def rename_city(self, old_name: str, new_name: str) -> bool:
        """Переименовать город с сохранением уникальности имени"""
        if old_name not in self.cities or new_name in self.cities:
            return False

        # переносим все дороги
        self.cities[new_name] = self.cities.pop(old_name)

        # обновляем ссылки в других городах
        for city in self.cities:
            if old_name in self.cities[city]:
                self.cities[city][new_name] = self.cities[city].pop(old_name)

        return True

    def add_road(self, city1: str, city2: str, cost: int) -> bool:
        """Добавить дорогу между городами с указанной стоимостью"""
        if city1 not in self.cities or city2 not in self.cities:
            return False

        if city2 not in self.cities[city1]:
            self.cities[city1][city2] = []
            self.cities[city2][city1] = []

        self.cities[city1][city2].append(cost)
        self.cities[city2][city1].append(cost)
        return True

    def remove_road(self, city1: str, city2: str, cost: Optional[int] = None) -> bool:
        """Удалить дорогу между городами"""
        if city1 not in self.cities or city2 not in self.cities:
            return False
        if city2 not in self.cities[city1]:
            return False

        if cost is None:
            # удаляем все дороги между городами
            del self.cities[city1][city2]
            del self.cities[city2][city1]
        else:
            # удаляем только дорогу с указанной стоимостью
            if cost in self.cities[city1][city2]:
                self.cities[city1][city2].remove(cost)
                self.cities[city2][city1].remove(cost)
                if not self.cities[city1][city2]:
                    del self.cities[city1][city2]
                    del self.cities[city2][city1]

        return True

    def update_road_cost(self, city1: str, city2: str, old_cost: int, new_cost: int) -> bool:
        """Изменить стоимость конкретной дороги между городами"""
        if city1 not in self.cities or city2 not in self.cities:
            return False
        if city2 not in self.cities[city1] or old_cost not in self.cities[city1][city2]:
            return False

        index = self.cities[city1][city2].index(old_cost)
        self.cities[city1][city2][index] = new_cost
        self.cities[city2][city1][index] = new_cost
        return True

    def get_cities(self) -> List[str]:
        """Получить список всех городов"""
        return list(self.cities.keys())

    def get_roads_from_city(self, city: str) -> List[Tuple[str, List[int]]]:
        """Получить список дорог из города с их стоимостями"""
        if city not in self.cities:
            return []
        return list(self.cities[city].items())

    def get_all_roads(self) -> List[Tuple[str, str, List[int]]]:
        """Получить список всех дорог"""
        roads = set()
        for city1 in self.cities:
            for city2 in self.cities[city1]:
                # Чтобы не дублировать дороги (A-B и B-A)
                if (city2, city1) not in roads:
                    roads.add((city1, city2))
        return [(city1, city2, self.cities[city1][city2]) for city1, city2 in roads]

    def to_dict(self) -> dict:
        """Улучшенная сериализация с поддержкой множественных дорог"""
        return {
            'cities': self.cities,
            '_serializer': 'CityMap_v2'  # версия формата
        }

    def from_dict(self, data: dict):
        """Улучшенная загрузка с проверкой структуры"""
        if not isinstance(data, dict):
            raise ValueError("Invalid data format")

        version = data.get('_version', '1.0')

        if version == '1.2':
            self.cities = {}
            cities_data = data.get('cities', {})
            for city, neighbors in cities_data.items():
                self.cities[city] = {}
                for neighbor, costs in neighbors.items():
                    self.cities[city][neighbor] = list(costs) if isinstance(costs, list) else [costs]
        else:
            self.cities = {}
            for city, neighbors in data.items():
                self.cities[city] = {}
                if isinstance(neighbors, dict):
                    for neighbor, costs in neighbors.items():
                        self.cities[city][neighbor] = list(costs) if isinstance(costs, list) else [costs]

# endregion

# region Паттерны
class Memento:
    """Хранитель для сохранения состояния карты"""

    def __init__(self, state: dict):
        self.state = state

    def get_state(self) -> dict:
        """Получить сохраненное состояние"""
        return self.state


class Command(ABC):
    """Абстрактный класс команды"""

    @abstractmethod
    def execute(self) -> bool:
        pass

    @abstractmethod
    def undo(self) -> bool:
        pass


class AddCityCommand(Command):
    def __init__(self, city_map: CityMap, name: str):
        self.city_map = city_map
        self.name = name
        # Для сериализации
        self._type = 'AddCityCommand'

    def execute(self) -> bool:
        result = self.city_map.add_city(self.name)
        return result

    def undo(self) -> bool:
        return self.city_map.remove_city(self.name)

    @property
    def __dict__(self):
        return {
            'type': self._type,
            'name': self.name
        }


class RemoveCityCommand(Command):
    def __init__(self, city_map: CityMap, name: str):
        self.city_map = city_map
        self.name = name
        self.roads = []
        self._type = 'RemoveCityCommand'

    def execute(self) -> bool:
        if self.name not in self.city_map.cities:
            return False

        for neighbor, costs in self.city_map.cities[self.name].items():
            self.roads.append((self.name, neighbor, costs.copy()))
        return self.city_map.remove_city(self.name)

    def undo(self) -> bool:
        if not self.city_map.add_city(self.name):
            return False

        for city1, city2, costs in self.roads:
            for cost in costs:
                self.city_map.add_road(city1, city2, cost)
        return True

    @property
    def __dict__(self):
        return {
            'type': self._type,
            'name': self.name,
            'roads': self.roads
        }


class RenameCityCommand(Command):
    def __init__(self, city_map: CityMap, old_name: str, new_name: str):
        self.city_map = city_map
        self.old_name = old_name
        self.new_name = new_name
        self._type = 'RenameCityCommand'

    def execute(self) -> bool:
        return self.city_map.rename_city(self.old_name, self.new_name)

    def undo(self) -> bool:
        return self.city_map.rename_city(self.new_name, self.old_name)

    @property
    def __dict__(self):
        return {
            'type': self._type,
            'old_name': self.old_name,
            'new_name': self.new_name
        }


class AddRoadCommand(Command):
    def __init__(self, city_map: CityMap, city1: str, city2: str, cost: int):
        self.city_map = city_map
        self.city1 = city1
        self.city2 = city2
        self.cost = cost
        self._type = 'AddRoadCommand'

    def execute(self) -> bool:
        return self.city_map.add_road(self.city1, self.city2, self.cost)

    def undo(self) -> bool:
        return self.city_map.remove_road(self.city1, self.city2, self.cost)

    @property
    def __dict__(self):
        return {
            'type': self._type,
            'city1': self.city1,
            'city2': self.city2,
            'cost': self.cost
        }


class RemoveRoadCommand(Command):
    def __init__(self, city_map: CityMap, city1: str, city2: str, cost: int):
        self.city_map = city_map
        self.city1 = city1
        self.city2 = city2
        self.cost = cost
        self._type = 'RemoveRoadCommand'

    def execute(self) -> bool:
        return self.city_map.remove_road(self.city1, self.city2, self.cost)

    def undo(self) -> bool:
        return self.city_map.add_road(self.city1, self.city2, self.cost)

    @property
    def __dict__(self):
        return {
            'type': self._type,
            'city1': self.city1,
            'city2': self.city2,
            'cost': self.cost
        }


class UpdateRoadCommand(Command):
    def __init__(self, city_map: CityMap, city1: str, city2: str, old_cost: int, new_cost: int):
        self.city_map = city_map
        self.city1 = city1
        self.city2 = city2
        self.old_cost = old_cost
        self.new_cost = new_cost
        self._type = 'UpdateRoadCommand'

    def execute(self) -> bool:
        return self.city_map.update_road_cost(self.city1, self.city2, self.old_cost, self.new_cost)

    def undo(self) -> bool:
        return self.city_map.update_road_cost(self.city1, self.city2, self.new_cost, self.old_cost)

    @property
    def __dict__(self):
        return {
            'type': self._type,
            'city1': self.city1,
            'city2': self.city2,
            'old_cost': self.old_cost,
            'new_cost': self.new_cost
        }


class CommandManager:
    def __init__(self, city_map: CityMap):
        self.city_map = city_map
        self.undo_stack = []
        self.redo_stack = []
        self.history = []
        self.current_history_index = -1
        self._save_state()

    def _save_state(self):
        """Сохраняет текущее состояние в историю"""
        state = {
            'map_state': self._get_safe_state(),
            'undo_stack': self._serialize_commands(self.undo_stack),
            'redo_stack': self._serialize_commands(self.redo_stack)
        }

        if self.current_history_index < len(self.history) - 1:
            self.history = self.history[:self.current_history_index + 1]

        self.history.append(state)
        self.current_history_index = len(self.history) - 1

    def _get_safe_state(self):
        """Гарантирует правильный формат данных"""
        return {
            'cities': {
                str(city): {
                    str(neighbor): list(costs)
                    for neighbor, costs in roads.items()
                }
                for city, roads in self.city_map.cities.items()
            },
            '_version': '1.2'
        }

    def _serialize_commands(self, commands):
        """Сериализация всех типов команд"""
        return [self._command_to_dict(cmd) for cmd in commands]

    def _command_to_dict(self, cmd):
        """Преобразование команды в словарь"""
        if isinstance(cmd, AddCityCommand):
            return {
                'type': 'AddCityCommand',
                'name': cmd.name
            }
        elif isinstance(cmd, RemoveCityCommand):
            return {
                'type': 'RemoveCityCommand',
                'name': cmd.name,
                'roads': cmd.roads
            }
        elif isinstance(cmd, RenameCityCommand):
            return {
                'type': 'RenameCityCommand',
                'old_name': cmd.old_name,
                'new_name': cmd.new_name
            }
        elif isinstance(cmd, AddRoadCommand):
            return {
                'type': 'AddRoadCommand',
                'city1': cmd.city1,
                'city2': cmd.city2,
                'cost': cmd.cost
            }
        elif isinstance(cmd, RemoveRoadCommand):
            return {
                'type': 'RemoveRoadCommand',
                'city1': cmd.city1,
                'city2': cmd.city2,
                'cost': cmd.cost
            }
        elif isinstance(cmd, UpdateRoadCommand):
            return {
                'type': 'UpdateRoadCommand',
                'city1': cmd.city1,
                'city2': cmd.city2,
                'old_cost': cmd.old_cost,
                'new_cost': cmd.new_cost
            }
        return {}

    def execute_command(self, command: Command) -> bool:
        """Выполняет команду с сохранением в историю"""
        if command.execute():
            self.undo_stack.append(command)
            self.redo_stack.clear()
            self._save_state()
            return True
        return False

    def undo(self) -> bool:
        """Отмена последней команды"""
        if not self.undo_stack:
            return False

        command = self.undo_stack.pop()
        if command.undo():
            self.redo_stack.append(command)
            self._save_state()
            return True
        return False

    def redo(self) -> bool:
        """Повтор отмененной команды"""
        if not self.redo_stack:
            return False

        command = self.redo_stack.pop()
        if command.execute():
            self.undo_stack.append(command)
            self._save_state()
            return True
        return False

    def save_to_file(self, filename: str) -> bool:
        try:
            data = {
                'history': [{
                    'map_state': self._get_safe_state(),
                    'undo_stack': self._serialize_commands(self.undo_stack),
                    'redo_stack': self._serialize_commands(self.redo_stack)
                }],
                'current_index': 0,
                '_metadata': {
                    'version': '1.2',
                    'created': datetime.now().isoformat()
                }
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Save error: {str(e)}")
            return False

    def load_from_file(self, filename: str) -> bool:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.history = data.get('history', [])
            self.current_history_index = data.get('current_index', 0)

            if not self.history:
                return False

            state = self.history[self.current_history_index]

            # проверка и преобразование map_state
            map_state = state.get('map_state', {})
            if isinstance(map_state, str):
                map_state = json.loads(map_state)

            self.city_map.from_dict(map_state)

            # восстановление команд
            self.undo_stack = self._deserialize_commands(state.get('undo_stack', []))
            self.redo_stack = self._deserialize_commands(state.get('redo_stack', []))

            return True
        except Exception as e:
            print(f"Load error: {str(e)}")
            return False

    def _deserialize_commands(self, commands_data):
        """Восстановление всех типов команд"""
        commands = []
        for cmd_data in commands_data:
            cmd = None
            try:
                if cmd_data['type'] == 'AddCityCommand':
                    cmd = AddCityCommand(self.city_map, cmd_data['name'])
                elif cmd_data['type'] == 'RemoveCityCommand':
                    cmd = RemoveCityCommand(self.city_map, cmd_data['name'])
                    cmd.roads = cmd_data.get('roads', [])
                elif cmd_data['type'] == 'RenameCityCommand':
                    cmd = RenameCityCommand(
                        self.city_map,
                        cmd_data['old_name'],
                        cmd_data['new_name']
                    )
                elif cmd_data['type'] == 'AddRoadCommand':
                    cmd = AddRoadCommand(
                        self.city_map,
                        cmd_data['city1'],
                        cmd_data['city2'],
                        cmd_data['cost']
                    )
                elif cmd_data['type'] == 'RemoveRoadCommand':
                    cmd = RemoveRoadCommand(
                        self.city_map,
                        cmd_data['city1'],
                        cmd_data['city2'],
                        cmd_data['cost']
                    )
                elif cmd_data['type'] == 'UpdateRoadCommand':
                    cmd = UpdateRoadCommand(
                        self.city_map,
                        cmd_data['city1'],
                        cmd_data['city2'],
                        cmd_data['old_cost'],
                        cmd_data['new_cost']
                    )

                if cmd:
                    commands.append(cmd)
            except:
                continue
        return commands

#endregion

# region Визуализация
class CityGraphicsView(QGraphicsView):
    """Виджет для визуализации карты городов"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setSceneRect(0, 0, 600, 600)

        # позиции городов для визуализации
        self.city_positions = {}

    def update_map(self, city_map: CityMap):
        """Обновить визуализацию карты"""
        self.scene.clear()
        self.city_positions = {}

        cities = city_map.get_cities()
        if not cities:
            return

        # распределяем города по кругу
        center = QPointF(300, 300)
        radius = 250
        angle_step = 360 / len(cities)

        for i, city in enumerate(cities):
            angle = i * angle_step
            x = center.x() + radius * math.cos(math.radians(angle))
            y = center.y() + radius * math.sin(math.radians(angle))
            self.city_positions[city] = QPointF(x, y)

            # рисуем город (круг с названием)
            ellipse = QGraphicsEllipseItem(x - 20, y - 20, 40, 40)
            ellipse.setBrush(QColor(255, 215, 0))  # золотой цвет
            self.scene.addItem(ellipse)

            text = self.scene.addText(city)
            text.setPos(x - text.boundingRect().width() / 2, y - 30)
            text.setDefaultTextColor(QColor(0, 0, 0))

        # рисуем дороги
        for city1, city2, costs in city_map.get_all_roads():
            pos1 = self.city_positions[city1]
            pos2 = self.city_positions[city2]

            # рисуем отдельную линию для каждой дороги
            for i, cost in enumerate(costs):
                line = QGraphicsLineItem(pos1.x(), pos1.y(), pos2.x(), pos2.y())

                # смещаем параллельные дороги для лучшей визуализации
                if len(costs) > 1:
                    offset = 10 * (i - (len(costs) - 1) / 2)
                    dx = pos2.y() - pos1.y()
                    dy = -(pos2.x() - pos1.x())
                    length = math.sqrt(dx * dx + dy * dy)
                    if length > 0:
                        dx = dx / length * offset
                        dy = dy / length * offset
                        line.setLine(pos1.x() + dx, pos1.y() + dy,
                                     pos2.x() + dx, pos2.y() + dy)

                pen = QPen(QColor(70, 130, 180), 2)
                line.setPen(pen)
                self.scene.addItem(line)

                # подпись стоимости дороги (посередине линии)
                mid_x = (pos1.x() + pos2.x()) / 2
                mid_y = (pos1.y() + pos2.y()) / 2
                if len(costs) > 1:
                    mid_x += dx / 2
                    mid_y += dy / 2

                text = self.scene.addText(str(cost))
                text.setPos(mid_x - text.boundingRect().width() / 2,
                            mid_y - text.boundingRect().height() / 2)
                text.setDefaultTextColor(QColor(0, 0, 0))

# endregion

# region Главное окно
class CityMapApp(QMainWindow):
    """Главное окно приложения"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Карта городов и дорог")
        self.setGeometry(100, 100, 1000, 700)

        self.city_map = CityMap()
        self.command_manager = CommandManager(self.city_map)

        self.init_ui()
        self.update_ui()

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # левая панель - управление
        left_panel = QVBoxLayout()
        main_layout.addLayout(left_panel, stretch=1)

        # правая панель - визуализация
        self.graphics_view = CityGraphicsView()
        main_layout.addWidget(self.graphics_view, stretch=2)

        # добавление города
        add_city_layout = QHBoxLayout()
        left_panel.addLayout(add_city_layout)

        self.city_name_input = QLineEdit()
        self.city_name_input.setPlaceholderText("Название города")
        add_city_layout.addWidget(self.city_name_input)

        add_city_btn = QPushButton("Добавить")
        add_city_btn.clicked.connect(self.add_city)
        add_city_layout.addWidget(add_city_btn)

        # список городов
        self.cities_list = QListWidget()
        self.cities_list.itemSelectionChanged.connect(self.on_city_selected)
        left_panel.addWidget(QLabel("Города:"))
        left_panel.addWidget(self.cities_list)

        # управление городом
        city_management_layout = QHBoxLayout()
        left_panel.addLayout(city_management_layout)

        self.rename_city_input = QLineEdit()
        self.rename_city_input.setPlaceholderText("Новое название")
        city_management_layout.addWidget(self.rename_city_input)

        rename_city_btn = QPushButton("Переименовать")
        rename_city_btn.clicked.connect(self.rename_city)
        city_management_layout.addWidget(rename_city_btn)

        remove_city_btn = QPushButton("Удалить")
        remove_city_btn.clicked.connect(self.remove_city)
        city_management_layout.addWidget(remove_city_btn)

        # управление дорогами
        road_management_layout = QVBoxLayout()
        left_panel.addLayout(road_management_layout)

        # выбор городов для дороги
        road_cities_layout = QHBoxLayout()
        road_management_layout.addLayout(road_cities_layout)

        self.city1_combo = QComboBox()
        self.city1_combo.currentIndexChanged.connect(self.update_roads_list)
        road_cities_layout.addWidget(self.city1_combo)

        self.city2_combo = QComboBox()
        road_cities_layout.addWidget(self.city2_combo)

        # стоимость дороги
        road_cost_layout = QHBoxLayout()
        road_management_layout.addLayout(road_cost_layout)

        self.road_cost_input = QSpinBox()
        self.road_cost_input.setMinimum(1)
        self.road_cost_input.setMaximum(1000)
        self.road_cost_input.setValue(1)
        road_cost_layout.addWidget(self.road_cost_input)

        add_road_btn = QPushButton("Добавить дорогу")
        add_road_btn.clicked.connect(self.add_road)
        road_cost_layout.addWidget(add_road_btn)

        # список дорог для выбранного города
        self.roads_list = QListWidget()
        self.roads_list.itemSelectionChanged.connect(self.on_road_selected)
        road_management_layout.addWidget(QLabel("Дороги из выбранного города:"))
        road_management_layout.addWidget(self.roads_list)

        # управление дорогой
        road_controls_layout = QHBoxLayout()
        road_management_layout.addLayout(road_controls_layout)

        self.new_cost_input = QSpinBox()
        self.new_cost_input.setMinimum(1)
        self.new_cost_input.setMaximum(1000)
        self.new_cost_input.setValue(1)
        road_controls_layout.addWidget(self.new_cost_input)

        update_road_btn = QPushButton("Изменить стоимость")
        update_road_btn.clicked.connect(self.update_road_cost)
        road_controls_layout.addWidget(update_road_btn)

        remove_road_btn = QPushButton("Удалить дорогу")
        remove_road_btn.clicked.connect(self.remove_road)
        road_controls_layout.addWidget(remove_road_btn)

        # undo/redo
        undo_redo_layout = QHBoxLayout()
        left_panel.addLayout(undo_redo_layout)

        undo_btn = QPushButton("Отменить (Ctrl+Z)")
        undo_btn.clicked.connect(self.undo)
        undo_redo_layout.addWidget(undo_btn)

        redo_btn = QPushButton("Повторить (Ctrl+Y)")
        redo_btn.clicked.connect(self.redo)
        undo_redo_layout.addWidget(redo_btn)

        self.init_menu()

    def init_menu(self):
        """Инициализация меню"""
        menubar = self.menuBar()

        # меню "Файл"
        file_menu = menubar.addMenu("Файл")

        save_action = QAction("Сохранить", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_to_file)
        file_menu.addAction(save_action)

        load_action = QAction("Загрузить", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.load_from_file)
        file_menu.addAction(load_action)

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # меню "Правка"
        edit_menu = menubar.addMenu("Правка")

        undo_action = QAction("Отменить", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("Повторить", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)

    def update_ui(self):
        """Обновить пользовательский интерфейс"""
        # обновить списки городов
        cities = self.city_map.get_cities()
        self.cities_list.clear()
        self.cities_list.addItems(cities)

        # обновить комбобоксы
        current_city1 = self.city1_combo.currentText()
        current_city2 = self.city2_combo.currentText()

        self.city1_combo.clear()
        self.city2_combo.clear()
        self.city1_combo.addItems(cities)
        self.city2_combo.addItems(cities)

        # восстановить выбранные города
        if current_city1 in cities:
            self.city1_combo.setCurrentText(current_city1)
        if current_city2 in cities:
            self.city2_combo.setCurrentText(current_city2)

        # обновить список дорог
        self.update_roads_list()

        # обновить визуализацию
        self.graphics_view.update_map(self.city_map)

    def update_roads_list(self):
        """Обновить список дорог для выбранного города"""
        self.roads_list.clear()
        city = self.city1_combo.currentText()
        if not city:
            return

        roads = self.city_map.get_roads_from_city(city)
        for neighbor, costs in roads:
            for cost in costs:
                self.roads_list.addItem(f"{neighbor} (стоимость: {cost})")

    def on_city_selected(self):
        """Обработчик выбора города"""
        selected_items = self.cities_list.selectedItems()
        if selected_items:
            city = selected_items[0].text()
            index = self.city1_combo.findText(city)
            if index >= 0:
                self.city1_combo.setCurrentIndex(index)
        self.update_roads_list()

    def on_road_selected(self):
        """Обработчик выбора дороги"""
        selected_items = self.roads_list.selectedItems()
        if selected_items:
            road_text = selected_items[0].text()
            city2 = road_text.split(" (")[0]
            cost = int(road_text.split(": ")[1].rstrip(")"))

            index = self.city2_combo.findText(city2)
            if index >= 0:
                self.city2_combo.setCurrentIndex(index)

            self.new_cost_input.setValue(cost)

    def add_city(self):
        """Добавить новый город"""
        city_name = self.city_name_input.text().strip()
        if not city_name:
            QMessageBox.warning(self, "Ошибка", "Введите название города")
            return

        command = AddCityCommand(self.city_map, city_name)
        if self.command_manager.execute_command(command):
            self.city_name_input.clear()
            self.update_ui()
        else:
            QMessageBox.warning(self, "Ошибка", "Город с таким именем уже существует")

    def remove_city(self):
        """Удалить выбранный город"""
        selected_items = self.cities_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите город для удаления")
            return

        city_name = selected_items[0].text()
        command = RemoveCityCommand(self.city_map, city_name)
        if self.command_manager.execute_command(command):
            self.update_ui()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось удалить город")

    def rename_city(self):
        """Переименовать выбранный город"""
        selected_items = self.cities_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите город для переименования")
            return

        old_name = selected_items[0].text()
        new_name = self.rename_city_input.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Ошибка", "Введите новое название города")
            return

        if old_name == new_name:
            QMessageBox.warning(self, "Ошибка", "Новое название должно отличаться от старого")
            return

        command = RenameCityCommand(self.city_map, old_name, new_name)
        if self.command_manager.execute_command(command):
            self.rename_city_input.clear()
            self.update_ui()
        else:
            QMessageBox.warning(self, "Ошибка",
                                "Не удалось переименовать город (возможно, город с таким именем уже существует)")

    def add_road(self):
        """Добавить дорогу между городами"""
        city1 = self.city1_combo.currentText()
        city2 = self.city2_combo.currentText()
        cost = self.road_cost_input.value()

        if not city1 or not city2:
            QMessageBox.warning(self, "Ошибка", "Выберите оба города")
            return

        if city1 == city2:
            QMessageBox.warning(self, "Ошибка", "Нельзя создать дорогу между одним и тем же городом")
            return

        command = AddRoadCommand(self.city_map, city1, city2, cost)
        if self.command_manager.execute_command(command):
            self.update_ui()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось добавить дорогу")

    def remove_road(self):
        """Удалить выбранную дорогу"""
        selected_items = self.roads_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите дорогу для удаления")
            return

        city1 = self.city1_combo.currentText()
        road_text = selected_items[0].text()
        city2 = road_text.split(" (")[0]
        cost = int(road_text.split(": ")[1].rstrip(")"))

        command = RemoveRoadCommand(self.city_map, city1, city2, cost)
        if self.command_manager.execute_command(command):
            self.update_ui()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось удалить дорогу")

    def update_road_cost(self):
        """Изменить стоимость выбранной дороги"""
        selected_items = self.roads_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите дорогу для изменения")
            return

        city1 = self.city1_combo.currentText()
        road_text = selected_items[0].text()
        city2 = road_text.split(" (")[0]
        old_cost = int(road_text.split(": ")[1].rstrip(")"))
        new_cost = self.new_cost_input.value()

        if old_cost == new_cost:
            QMessageBox.warning(self, "Ошибка", "Новая стоимость должна отличаться от текущей")
            return

        command = UpdateRoadCommand(self.city_map, city1, city2, old_cost, new_cost)
        if self.command_manager.execute_command(command):
            self.update_ui()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось изменить стоимость дороги")

    def undo(self):
        """Отменить последнее действие"""
        if self.command_manager.undo():
            self.update_ui()

    def redo(self):
        """Повторить отмененное действие"""
        if self.command_manager.redo():
            self.update_ui()

    def save_to_file(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить карту", "", "JSON Files (*.json)")
        if filename:
            if not filename.endswith('.json'):
                filename += '.json'
            if self.command_manager.save_to_file(filename):
                QMessageBox.information(self, "Успех", "Файл сохранен с историей изменений!")
            else:
                QMessageBox.critical(self, "Ошибка", "Ошибка при сохранении файла")

    def load_from_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Загрузить карту", "", "JSON Files (*.json)")
        if filename:
            if self.command_manager.load_from_file(filename):
                self.update_ui()
                QMessageBox.information(self, "Успех", "Файл загружен с историей изменений!")
            else:
                QMessageBox.critical(self, "Ошибка", "Ошибка при загрузке файла")

#endregion


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CityMapApp()
    window.show()
    sys.exit(app.exec_())
