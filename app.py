import io
import zipfile
import qrcode
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import streamlit as st

st.set_page_config(
    page_title="QR Batch Generator", page_icon="🔲", layout="centered"
)

st.title("🔲 Генератор пачки QR-кодов")
st.write(
    "Вставьте ссылки (по одной на строку), выберите формат и скачайте готовый архив."
)

# Инпуты для пользователя
links_input = st.text_area(
    "Список ссылок (каждая с новой строки):",
    placeholder="https://example.com/1\nhttps://example.com/2",
    height=150,
)

col1, col2 = st.columns(2)
with col1:
    output_format = st.selectbox("Формат файлов", ["PNG", "PDF"], index=0)
with col2:
    # Поворот для PDF, если стандартные просмотрщики открывают их боком
    rotate_pdf = st.checkbox("Повернуть PDF на -90°", value=True)

box_size = st.slider("Размер / Качество QR", min_value=5, max_value=20, value=10)


def generate_qr_image(url, box_size):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def create_pdf_from_image(img, rotate=True):
    pdf_buffer = io.BytesIO()
    # Сохраняем во временный буфер как картинку
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    # Создаем PDF через ReportLab нужного размера под картинку
    width, height = img.size
    c = canvas.Canvas(pdf_buffer, pagesize=(width, height))

    if rotate:
        # Поворот на -90 градусов против часовой стрелки
        c.translate(0, height)
        c.rotate(-90)
        c.drawImage(
            img_byte_arr, 0, 0, width=height, height=width
        , mask='auto')
    else:
        c.drawImage(img_byte_arr, 0, 0, width=width, height=height)

    c.showPage()
    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


if st.button("Сгенерировать и скачать архив", type="primary"):
    links = [line.strip() for line in links_input.split("\n") if line.strip()]

    if not links:
        st.warning("Пожалуйста, введите хотя бы одну ссылку.")
    else:
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(
            zip_buffer, "w", zipfile.ZIP_DEFLATED
        ) as zip_file:
            for i, link in enumerate(links, 1):
                # Чистим имя файла из ссылки для безопасности
                safe_name = (
                    link.replace("https://", "")
                    .replace("http://", "")
                    .replace("/", "_")[:30]
                )
                file_name = f"qr_{i:02d}_{safe_name}"

                img = generate_qr_image(link, box_size)

                if output_format == "PNG":
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format="PNG")
                    zip_file.writestr(f"{file_name}.png", img_byte_arr.getvalue())
                elif output_format == "PDF":
                    pdf_data = create_pdf_from_image(img, rotate=rotate_pdf)
                    zip_file.writestr(f"{file_name}.pdf", pdf_data)

        zip_buffer.seek(0)

        st.success(f"Готово! Обработано ссылок: {len(links)}")
        st.download_data = zip_buffer.getvalue()

        st.download_button(
            label="📦 Скачать ZIP с QR-кодами",
            data=zip_buffer,
            file_name="qr_codes_batch.zip",
            mime="application/zip",
        )