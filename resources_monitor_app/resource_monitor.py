import sys
import sqlite3
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel, QWidget,
    QTableWidget, QTableWidgetItem, QDialog, QSpinBox
)
from PyQt5.QtCore import QTimer
import psutil


# Настройка БД
def setup_database(db_path="resources.db"):
    conn = sqlite3.connect(db_path)  # Устанавливаем соединение с SQLite.
    cursor = conn.cursor()  # Создаем объект для выполнения SQL-запросов.
    cursor.execute('''CREATE TABLE IF NOT EXISTS resource_usage (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp TEXT,
                      cpu_usage REAL,
                      ram_usage REAL,
                      disk_usage REAL)''')
    conn.commit()  # Применяем изменения.
    conn.close()  # Закрываем соединение.


class ResourceMonitor(QMainWindow):
    """Основной класс приложения, реализует главное окно приложения, используя PyQt5."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Resource Monitor")
        self.resize(400, 300)

        self.recording = False  # Флаг записи данных.
        self.start_time = None  # Время начала записи.
        self.update_interval = 1000  # Интервал обновления (мс).

        self.db_path = "resources.db"  # Путь к базе данных.

        self.init_ui()  # Инициализация интерфейса.

        self.timer = QTimer()  # Таймер для периодических событий.
        self.timer.timeout.connect(self.update_metrics)  # Связываем с обновлением метрик.
        self.timer.start(self.update_interval)  # Запускаем таймер.

    def init_ui(self):
        """Инициализация пользовательского интерфейса."""
        layout = QVBoxLayout()  # Размещаем элементы в вертикальном порядке.

        self.cpu_label = QLabel("CPU Usage: 0%")  # Метка для отображения метрик cpu.
        self.ram_label = QLabel("RAM Usage: 0%")  # Метка для отображения метрик ram.
        self.disk_label = QLabel("Disk Usage: 0%")  # Метка для отображения метрик disk_usage.
        self.timer_label = QLabel("Recording Time: 00:00")  # Метка для отображения времени записи.

        self.start_button = QPushButton("Start Recording")  # Кнопка для старта записи.
        self.start_button.clicked.connect(self.start_recording)

        self.stop_button = QPushButton("Stop Recording")  # Кнопка для остановки записи.
        self.stop_button.clicked.connect(self.stop_recording)
        self.stop_button.setVisible(False)

        self.history_button = QPushButton("View History")  # Кнопка для обзора истории.
        self.history_button.clicked.connect(self.view_history)

        self.interval_spinner = QSpinBox()  # Поле для выбора интервала обновления (в секундах).
        self.interval_spinner.setMinimum(1)
        self.interval_spinner.setMaximum(60)
        self.interval_spinner.setValue(1)
        self.interval_spinner.valueChanged.connect(self.change_interval)

        # Добавляем элементы в интерфейс.
        layout.addWidget(self.cpu_label)
        layout.addWidget(self.ram_label)
        layout.addWidget(self.disk_label)
        layout.addWidget(self.timer_label)
        layout.addWidget(self.interval_spinner)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.history_button)

        container = QWidget()
        container.setLayout(layout)  # Устанавливаем компоновку layout для контейнера.
        self.setCentralWidget(container)  # Устанавливаем виджет container в качестве центрального элемента окна.

    def format_time(self, seconds):
        """Форматирует время в формате 00:00."""
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02}:{seconds:02}"

    def update_metrics(self):
        """Обновление метрик"""
        cpu = psutil.cpu_percent()  # Получение загрузки процессора в процентах.
        ram = psutil.virtual_memory().percent  # Получение использования ОЗУ.
        disk = psutil.disk_usage('/').percent  # Получение использования диска.

        # Обновляем текст метки.
        self.cpu_label.setText(f"CPU Usage: {cpu}%")
        self.ram_label.setText(f"RAM Usage: {ram}%")
        self.disk_label.setText(f"Disk Usage: {disk}%")

        if self.recording:
            elapsed_time = int(time.time() - self.start_time)  # Вычисляем прошедшее время записи.
            formatted_time = self.format_time(elapsed_time)
            self.timer_label.setText(f"Recording Time: {formatted_time}")

            conn = sqlite3.connect(self.db_path)  # Подключение к базе данных.
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO resource_usage (timestamp, cpu_usage, ram_usage, disk_usage)"
                "VALUES (datetime('now'), ?, ?, ?)",
                (cpu, ram, disk))  # Вставляем запись с текущими метриками.
            conn.commit()
            conn.close()

    def start_recording(self):
        """Начало записи."""
        self.recording = True  # Включаем запись.
        self.start_time = time.time()  # Фиксируем время начала.
        self.start_button.setVisible(False)  # Прячем кнопку "Start Recording".
        self.stop_button.setVisible(True)  # Показываем кнопку "Stop Recording".

    def stop_recording(self):
        """Остановка записи."""
        self.recording = False  # Останавливаем запись.
        self.start_time = None  # Сбрасываем время начала.
        self.timer_label.setText("Recording Time: 00:00")  # Обнуляем таймер.
        self.start_button.setVisible(True)  # Показываем кнопку "Start Recording".
        self.stop_button.setVisible(False)  # Прячем кнопку "Stop Recording".

    def view_history(self):
        """Отображение истории"""
        dialog = QDialog(self)  # Создаем модальное окно для отображения истории.
        dialog.setWindowTitle("History")
        dialog.resize(600, 400)

        layout = QVBoxLayout()

        table = QTableWidget()  # Таблица для отображения данных.
        table.setColumnCount(4)  # Задаем кол-во колонок.

        # Устанавливаем заголовки колонок.
        table.setHorizontalHeaderLabels(["Timestamp", "CPU Usage", "RAM Usage", "Disk Usage"])

        # Подключаемся к БД.
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, cpu_usage, ram_usage, disk_usage FROM resource_usage")
        rows = cursor.fetchall()
        conn.close()

        table.setRowCount(len(rows))  # Задаем количество строк.
        for row_idx, row_data in enumerate(rows):
            for col_idx, col_data in enumerate(row_data):
                table.setItem(row_idx, col_idx, QTableWidgetItem(str(col_data)))

        layout.addWidget(table)

        # загружаем данные в БД
        def load_data():
            if dialog.isVisible():  # Проверка видимости диалога
                conn = sqlite3.connect(self.db_path)  # Подключение к базе данных.
                cursor = conn.cursor()
                cursor.execute("SELECT timestamp, cpu_usage, ram_usage, disk_usage FROM resource_usage")
                rows = cursor.fetchall()  # Извлечение всех строк из таблицы.
                conn.close()

                table.setRowCount(len(rows))  # Установка количества строк в таблице.
                for row_idx, row_data in enumerate(rows):  # Проходим по строкам данных.
                    for col_idx, col_data in enumerate(row_data):  # По колонкам в каждой строке.
                        table.setItem(row_idx, col_idx, QTableWidgetItem(str(col_data)))  # Заполняем ячейку данными.

        load_data()

        self.history_timer = QTimer(self)
        self.history_timer.timeout.connect(load_data)
        self.history_timer.start(self.update_interval)

        # Кнопка "Clear History", удаляем историю и очищаем БД.
        def clear_history():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM resource_usage")
            conn.commit()
            conn.close()
            table.setRowCount(0)  # Очищаем таблицу в интерфейсе

        clear_button = QPushButton("Clear History")
        clear_button.clicked.connect(clear_history)
        layout.addWidget(clear_button)

        dialog.setLayout(layout)
        dialog.exec_()

        dialog.finished.connect(self.history_timer.stop)

    def change_interval(self):
        """Изменение интервала"""
        self.update_interval = self.interval_spinner.value() * 1000  # Получаем выбранное значение интервала в секундах.
        self.timer.setInterval(self.update_interval)  # Устанавливаем новый интервал таймера.


if __name__ == "__main__":
    setup_database()  # Создание базы данных.
    app = QApplication(sys.argv)  # Инициализация приложения PyQt5.
    window = ResourceMonitor()  # Создание главного окна.
    window.show()  # Отображение окна.
    sys.exit(app.exec_())  # Запуск главного цикла приложения.
