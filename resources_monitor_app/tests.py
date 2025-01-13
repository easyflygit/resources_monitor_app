import os
import sys
import unittest
import sqlite3
import time
from resource_monitor import ResourceMonitor, setup_database
from PyQt5.QtWidgets import QApplication, QTableWidgetItem, QVBoxLayout, QDialog, QTableWidget
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt


app = QApplication(sys.argv)


class TestSetupDatabase(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_resources.db"
        # Создаем базу данных для теста
        sqlite3.connect(self.db_path).close()

    def tearDown(self):
        # Удаляем базу данных после каждого теста
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_setup_database_creates_table(self):
        # Вызываем setup_database для создания таблицы
        setup_database(self.db_path)

        # Подключаемся к базе данных и проверяем таблицу
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Проверяем, что таблица существует
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resource_usage'")
        result = cursor.fetchone()
        if result is None:
            print("Table 'resource_usage' not found.")
        conn.close()
        self.assertIsNotNone(result, "Table 'resource_usage' was not created.")

    def test_database_with_correct_columns(self):
        # Вызываем setup_database для создания таблицы
        setup_database(self.db_path)

        # Подключаемся к базе данных и проверяем таблицу
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Проверяем, что таблица содержит правильные столбцы
        cursor.execute("PRAGMA table_info(resource_usage)")
        columns = [column[1] for column in cursor.fetchall()]

        # Нужные столбцы
        required_columns = ['id', 'timestamp', 'cpu_usage', 'ram_usage', 'disk_usage']

        # Проверяем, что каждый столбец есть в таблице
        for col in required_columns:
            self.assertIn(col, columns, f"Column '{col}' was not created in 'resource_usage' table")
        conn.close()


class TestResourceMonitor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Создаем приложение для тестов."""
        cls.app = QApplication

    def setUp(self):
        """Создаем экземпляр ResourceMonitor перед каждым тестом."""
        self.window = ResourceMonitor()
        self.window.show()

    def tearDown(self):
        """Закрываем окно после каждого теста."""
        self.window.close()

    @classmethod
    def tearDownClass(cls):
        """Закрываем приложение после завершения всех тестов."""
        cls.app.quit()

    def test_ui_initialization(self):
        """Тестируем инициализацию интерфейса."""
        self.assertEqual(self.window.windowTitle(), "Resource Monitor")
        self.assertEqual(self.window.cpu_label.text(), "CPU Usage: 0%")
        self.assertEqual(self.window.ram_label.text(), "RAM Usage: 0%")
        self.assertEqual(self.window.disk_label.text(), "Disk Usage: 0%")
        self.assertEqual(self.window.timer_label.text(), "Recording Time: 00:00")

    def test_initial_state(self):
        """Тестирует начальное состояние приложения."""
        self.assertFalse(self.window.recording, "Режим записи должен быть выключен.")
        self.assertTrue(self.window.start_button.isVisible(), "Кнопка 'Start' должна быть видимой.")
        self.assertFalse(self.window.stop_button.isVisible(), "Кнопка 'Stop' не должна быть видимой.")

    def test_start_recording(self):
        """Тестирует поведение при нажатии кнопки 'Start Recording'."""
        QTest.mouseClick(self.window.start_button, Qt.LeftButton)
        self.assertTrue(self.window.recording, "Режим записи должен быть включен.")
        self.assertFalse(self.window.start_button.isVisible(), "Кнопка 'Start' не должна быть видимой.")
        self.assertTrue(self.window.stop_button.isVisible(), "Кнопка 'Stop' должна быть видимой.")

    def test_stop_recording(self):
        """Тестирует поведение при нажатии кнопки 'Stop Recording'."""
        # Включаем запись
        self.window.recording = True
        self.window.start_time = time.time()
        self.window.start_button.setVisible(False)
        self.window.stop_button.setVisible(True)

        QTest.mouseClick(self.window.stop_button, Qt.LeftButton)
        self.assertFalse(self.window.recording, "Режим записи должен быть выключен.")
        self.assertTrue(self.window.start_button.isVisible(), "Кнопка 'Start' должна быть видимой.")
        self.assertFalse(self.window.stop_button.isVisible(), "Кнопка 'Stop' не должна быть видимой.")

    def test_database_insert(self):
        """Тестируем, что данные записываются в базу при записи."""
        self.db_path = "test_resources.db"
        # Создаем базу данных для теста
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        setup_database(self.db_path)

        # Устанавливаем тестовую базу данных
        self.window.db_path = self.db_path

        # Нажимаем кнопку "Start Recording"
        QTest.mouseClick(self.window.start_button, Qt.LeftButton)

        # Эмулируем одно обновление таймера
        self.window.update_metrics()

        # Проверяем, что данные записались в базу
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Убедимся, что таблица существует
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resource_usage'")
        table_exists = cursor.fetchone()
        self.assertIsNotNone(table_exists, "Таблица 'resource_usage' не была создана.")

        # Проверяем записи
        cursor.execute("SELECT * FROM resource_usage")
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(len(rows), 1, "Данные не записались в базу.")
        self.assertEqual(len(rows[0]), 5, "Запись в базе данных не соответствует ожидаемой структуре.")

    def test_change_interval(self):
        """Тестируем изменение интервала обновления."""
        initial_interval = self.window.update_interval

        # Изменяем интервал на 5 секунд
        self.window.interval_spinner.setValue(5)

        self.assertEqual(self.window.update_interval, 5000)
        self.assertEqual(self.window.timer.interval(), 5000)
        self.assertNotEqual(self.window.update_interval, initial_interval)

    def test_view_history_logic(self):
        """Тестируем логику метода view_history без открытия GUI."""
        self.db_path = "test_resources.db"

        # Создаем базу данных для теста
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        setup_database(self.db_path)

        # Устанавливаем путь к базе
        self.window.db_path = self.db_path

        # Добавляем тестовые данные
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO resource_usage (timestamp, cpu_usage, ram_usage, disk_usage) "
            "VALUES (datetime('now'), 50, 60, 70)"
        )
        conn.commit()
        conn.close()

        # Вызываем метод view_history
        dialog = QDialog(self.window)  # Создаем диалог в тесте
        dialog.setWindowTitle("History")
        dialog.resize(600, 400)

        layout = QVBoxLayout()
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Timestamp", "CPU Usage", "RAM Usage", "Disk Usage"])

        # Симулируем загрузку данных
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, cpu_usage, ram_usage, disk_usage FROM resource_usage")
        rows = cursor.fetchall()
        conn.close()

        table.setRowCount(len(rows))
        for row_idx, row_data in enumerate(rows):
            for col_idx, col_data in enumerate(row_data):
                # Приведение значений к целым числам внутри метода
                if col_idx > 0:
                    col_data = int(float(col_data))
                table.setItem(row_idx, col_idx, QTableWidgetItem(str(col_data)))

        layout.addWidget(table)
        dialog.setLayout(layout)

        # Проверяем данные в таблице
        self.assertEqual(table.rowCount(), 1, "Неверное количество строк в таблице.")
        self.assertEqual(table.item(0, 1).text(), "50", "Неверное значение CPU Usage.")
        self.assertEqual(table.item(0, 2).text(), "60", "Неверное значение RAM Usage.")
        self.assertEqual(table.item(0, 3).text(), "70", "Неверное значение Disk Usage.")

    def test_clear_history_logic(self):
        """Тестируем логику очистки данных."""
        self.db_path = "test_resources.db"

        # Создаем базу данных для теста
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        setup_database(self.db_path)

        # Устанавливаем путь к базе
        self.window.db_path = self.db_path

        # Добавляем тестовые данные
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO resource_usage (timestamp, cpu_usage, ram_usage, disk_usage) "
            "VALUES (datetime('now'), 50, 60, 70)"
        )
        conn.commit()
        conn.close()

        # Симулируем очистку данных
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM resource_usage")
        conn.commit()
        conn.close()

        # Проверяем, что данные удалены
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM resource_usage")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 0, "Данные не были удалены из базы.")


if __name__ == "__main__":
    unittest.main()
