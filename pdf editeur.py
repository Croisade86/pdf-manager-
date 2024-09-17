import sys
import fitz  # PyMuPDF
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QScrollArea, QCheckBox
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag, QPixmap, QImage
from PyPDF2 import PdfReader, PdfWriter

class PDFPage(QWidget):
    def __init__(self, page_number, pixmap, pdf_path, parent=None):
        super().__init__(parent)
        self.page_number = page_number
        self.pdf_path = pdf_path
        self.pixmap = pixmap

        layout = QVBoxLayout(self)
        self.checkbox = QCheckBox()
        layout.addWidget(self.checkbox)

        self.label = QLabel()
        self.label.setPixmap(pixmap)
        self.label.setFixedSize(200, 280)  # Adjust size as needed
        self.label.setScaledContents(True)
        self.label.setFrameStyle(QLabel.Panel | QLabel.Raised)
        layout.addWidget(self.label)

        self.setFixedSize(220, 330)  # Adjust size to accommodate checkbox

    def mouseMoveEvent(self, e):
        if e.buttons() != Qt.LeftButton:
            return

        mime_data = QMimeData()
        mime_data.setText(f"{self.pdf_path}|{self.page_number}")

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.setPixmap(self.pixmap.scaled(100, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        drag.exec_(Qt.MoveAction)

class PDFColumn(QWidget):
    def __init__(self, pdf_path, is_destination=False, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.is_destination = is_destination
        self.pages = []

        layout = QVBoxLayout(self)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area)

        content_widget = QWidget()
        self.page_layout = QVBoxLayout(content_widget)
        self.scroll_area.setWidget(content_widget)

        self.load_pdf_pages(pdf_path)

        button_layout = QHBoxLayout()
        save_button = QPushButton("Enregistrer cette colonne")
        save_button.clicked.connect(self.save_column)
        button_layout.addWidget(save_button)

        delete_button = QPushButton("Supprimer la sélection")
        delete_button.clicked.connect(self.delete_selected_pages)
        button_layout.addWidget(delete_button)

        select_all_button = QPushButton("Sélectionner tout")
        select_all_button.clicked.connect(self.select_all_pages)
        button_layout.addWidget(select_all_button)

        deselect_all_button = QPushButton("Désélectionner tout")
        deselect_all_button.clicked.connect(self.deselect_all_pages)
        button_layout.addWidget(deselect_all_button)

        layout.addLayout(button_layout)

        self.setAcceptDrops(True)

    def load_pdf_pages(self, pdf_path):
        pdf_document = fitz.open(pdf_path)
        for i in range(len(pdf_document)):
            page = pdf_document.load_page(i)
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            pdf_page = PDFPage(i + 1, pixmap, pdf_path)
            self.page_layout.addWidget(pdf_page)
            self.pages.append(pdf_page)

    def dragEnterEvent(self, e):
        e.accept()

    def dropEvent(self, e):
        pos = e.pos()
        mime_data = e.mimeData()

        if mime_data.hasText():
            pdf_path, page_number = mime_data.text().split('|')
            page_number = int(page_number)

            if pdf_path == self.pdf_path:
                self.reorder_page(page_number, pos)
            else:
                self.copy_page(pdf_path, page_number, pos)

    def reorder_page(self, page_number, pos):
        moving_page = None
        for i, page in enumerate(self.pages):
            if page.page_number == page_number:
                moving_page = page
                self.page_layout.removeWidget(page)
                self.pages.remove(page)
                break

        if moving_page:
            for i, page in enumerate(self.pages):
                if page.geometry().contains(pos):
                    self.page_layout.insertWidget(i, moving_page)
                    self.pages.insert(i, moving_page)
                    return

            self.page_layout.addWidget(moving_page)
            self.pages.append(moving_page)

    def copy_page(self, pdf_path, page_number, pos):
        pdf_document = fitz.open(pdf_path)
        page = pdf_document.load_page(page_number - 1)
        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        new_page = PDFPage(page_number, pixmap, pdf_path)

        for i, page in enumerate(self.pages):
            if page.geometry().contains(pos):
                self.page_layout.insertWidget(i, new_page)
                self.pages.insert(i, new_page)
                return

        self.page_layout.addWidget(new_page)
        self.pages.append(new_page)

    def save_column(self):
        output_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer le PDF de cette colonne", "", "PDF Files (*.pdf)")
        if output_path:
            writer = PdfWriter()
            for page in self.pages:
                reader = PdfReader(page.pdf_path)
                writer.add_page(reader.pages[page.page_number - 1])

            with open(output_path, "wb") as output_file:
                writer.write(output_file)

    def delete_selected_pages(self):
        pages_to_remove = [page for page in self.pages if page.checkbox.isChecked()]
        for page in pages_to_remove:
            self.page_layout.removeWidget(page)
            self.pages.remove(page)
            page.deleteLater()

    def select_all_pages(self):
        for page in self.pages:
            page.checkbox.setChecked(True)

    def deselect_all_pages(self):
        for page in self.pages:
            page.checkbox.setChecked(False)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visual PDF Merger")
        self.pdf_columns = []

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        control_layout = QVBoxLayout()
        main_layout.addLayout(control_layout)

        load_pdf_button = QPushButton("Charger PDF")
        load_pdf_button.clicked.connect(self.load_pdf)
        control_layout.addWidget(load_pdf_button)

        save_all_button = QPushButton("Enregistrer PDF Fusionné Global")
        save_all_button.clicked.connect(self.save_merged_pdf)
        control_layout.addWidget(save_all_button)

        self.pdf_layout = QHBoxLayout()
        main_layout.addLayout(self.pdf_layout)

    def load_pdf(self):
        file_dialog = QFileDialog()
        pdf_paths, _ = file_dialog.getOpenFileNames(self, "Sélectionner un ou plusieurs PDF", "", "PDF Files (*.pdf)")

        for pdf_path in pdf_paths:
            pdf_column = PDFColumn(pdf_path)
            self.pdf_columns.append(pdf_column)
            self.pdf_layout.addWidget(pdf_column)

    def save_merged_pdf(self):
        output_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer le PDF fusionné global", "", "PDF Files (*.pdf)")
        if output_path:
            writer = PdfWriter()
            for column in self.pdf_columns:
                for page in column.pages:
                    reader = PdfReader(page.pdf_path)
                    writer.add_page(reader.pages[page.page_number - 1])

            with open(output_path, "wb") as output_file:
                writer.write(output_file)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
