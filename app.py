import io
import zipfile
import qrcode
from qrcode.image.svg import SvgPathImage
from PIL import Image, ImageOps
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import streamlit as st

st.set_page_config(
    page_title="QR Batch Generator", page_icon="🔲", layout="centered"
)

st.title("🔲 Генератор пачки QR-кодов")
st.write(
    "Вставьте ссылки, настройте параметры и скачайте готовый архив в нужном формате."
)

links_input = st.text_area(
    "Список ссылок (каждая с новой строки):",
    placeholder="https://example.com/1\nhttps://example.com/2",
    height=150,
)

col1, col2, col3 = st.columns(3)
with col1:
    output_format = st.selectbox("Формат файлов", ["PNG", "SVG", "PDF"], index=0)
with col2:
    rotate_pdf = st.checkbox("Повернуть PDF на -90°", value=True)
with col3:
    box_size = st.slider(
        "Размер точки (box_size)", min_value=5, max_value=20, value=10
    )

estimated_px = 37 * box_size
st.caption(
    f"💡 При таком значении (`{box_size}`) итоговый размер растрового QR-кода составит примерно **{estimated_px} × {estimated_px} px**. Для печати на полиграфии рекомендуем **SVG**."
)

st.write("---")

add_logo = st.checkbox("Добавить логотип в центр QR-кода")

uploaded_logo = None
if add_logo:
    uploaded_logo = st.file_uploader(
        "Загрузите логотип (будет автоматически переведен в Ч/Б с белым полем)",
        type=["png", "jpg", "jpeg"],
    )


def generate_qr_image(url, box_size, logo_img=None, as_svg=False):
    if as_svg:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(image_factory=SvgPathImage)
        return img.to_string(encoding="utf-8")
    else:
        error_corr = (
            qrcode.constants.ERROR_CORRECT_H
            if logo_img
            else qrcode.constants.ERROR_CORRECT_M
        )
        qr = qrcode.QRCode(
            version=None,
            error_correction=error_corr,
            box_size=box_size,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white").convert(
            "RGB"
        )

        if logo_img:
            try:
                # Открываем логотип и конвертируем в Ч/Б (L - оттенки серого)
                logo = Image.open(logo_img).convert("L")
                
                # Инвертируем или делаем контрастнее, если нужно, но базово просто переводим в черно-белое
                # Сделаем жесткий порог (threshold), чтобы логотип был чисто черно-белым без серых полутонов
                logo = logo.point(lambda p: 0 if p < 140 else 255, '1').convert("RGBA")

                qr_width, qr_height = img.size
                logo_max_size = min(qr_width, qr_height) // 4

                # Изменяем размер самого логотипа
                logo.thumbnail((logo_max_size, logo_max_size), Image.LANCZOS)

                # Создаем белую квадратную подложку (охранное поле) чуть больше самого логотипа
                padding = 8  # толщина белой рамки вокруг логотипа в пикселях
                bg_size = (logo.size[0] + padding * 2, logo.size[1] + padding * 2)
                
                background = Image.new("RGBA", bg_size, "white")
                
                # Вставляем логотип по центру белой подложки
                bg_x = (bg_size[0] - logo.size[0]) // 2
                bg_y = (bg_size[1] - logo.size[1]) // 2
                background.paste(logo, (bg_x, bg_y), logo)

                # Вычисляем координаты для вставки всей композиции (лого + поле) в центр QR
                pos_x = (qr_width - background.size[0]) // 2
                pos_y = (qr_height - background.size[1]) // 2

                # Накладываем на QR-код
                img.paste(background, (pos_x, pos_y), background)

            except Exception as e:
                st.warning(f"Не удалось добавить логотип: {e}")

        return img


def create_pdf_from_image(img, rotate=True):
    if rotate:
        img = img.rotate(270, expand=True)

    pdf_buffer = io.BytesIO()
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    width, height = img.size
    c = canvas.Canvas(pdf_buffer, pagesize=(width, height))
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
                safe_name = (
                    link.replace("https://", "")
                    .replace("http://", "")
                    .replace("/", "_")[:30]
                )
                file_name = f"qr_{i:02d}_{safe_name}"

                if output_format == "SVG":
                    svg_data = generate_qr_image(
                        link, box_size, as_svg=True
                    )
                    zip_file.writestr(
                        f"{file_name}.svg",
                        svg_data
                        if isinstance(svg_data, bytes)
                        else svg_data.encode("utf-8"),
                    )
                elif output_format == "PNG":
                    img = generate_qr_image(
                        link, box_size, logo_img=uploaded_logo, as_svg=False
                    )
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format="PNG")
                    zip_file.writestr(f"{file_name}.png", img_byte_arr.getvalue())
                elif output_format == "PDF":
                    img = generate_qr_image(
                        link, box_size, logo_img=uploaded_logo, as_svg=False
                    )
                    pdf_data = create_pdf_from_image(img, rotate=rotate_pdf)
                    zip_file.writestr(f"{file_name}.pdf", pdf_data)

        zip_buffer.seek(0)

        st.success(f"Готово! Обработано ссылок: {len(links)}")
        st.download_button(
            label="📦 Скачать ZIP с QR-кодами",
            data=zip_buffer,
            file_name="qr_codes_batch.zip",
            mime="application/zip",
        )
