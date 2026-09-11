import io
import zipfile
import qrcode
from qrcode.image.svg import SvgPathImage
from PIL import Image, ImageOps, ImageDraw
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import streamlit as st

st.set_page_config(
    page_title="QR Batch Generator Pro", page_icon="🔲", layout="wide"
)

st.title("🔲 Профессиональный генератор и пачка QR-кодов")
st.write(
    "Настройте стиль, углы, логотип, проверьте превью и скачайте готовые QR-коды."
)

# Две колонки: слева настройки и ссылки, справа — интерактивный превью-блок
col_main, col_preview = st.columns([1.6, 1])

with col_main:
    links_input = st.text_area(
        "Список ссылок (каждая с новой строки):",
        placeholder="https://example.com/1\nhttps://example.com/2",
        height=120,
        value="https://get-qr.com/q_H6zb",
    )

    st.markdown("### 🎨 Настройка стиля и дизайна")

    # Стили углов и точек (как в референсе)
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        corner_style = st.selectbox(
            "Стиль внешних рамок углов (Finder Pattern)",
            ["Классический квадрат", "Круглые рамки", "Закругленные рамки"],
            index=1,  # По умолчанию как на скрине (круглые)
        )
    with col_s2:
        dot_style = st.selectbox(
            "Форма точек узора",
            ["Круглые точки", "Квадратные точки", "Мелкие точки"],
            index=0,
        )

    col_opt1, col_opt2, col_opt3 = st.columns(3)
    with col_opt1:
        output_format = st.selectbox("Формат файлов", ["PNG", "SVG", "PDF"], index=0)
    with col_opt2:
        rotate_images = st.checkbox("Повернуть на -90°", value=True)
    with col_opt3:
        box_size = st.slider(
            "Размер точки (box_size)", min_value=6, max_value=16, value=10
        )

    st.markdown("---")
    st.markdown("### 🖼️ Логотип")
    add_logo = st.checkbox("Добавить логотип в центр QR-кода", value=True)

    logo_choice = "Сбер QR"
    uploaded_logo = None

    if add_logo:
        logo_choice = st.radio(
            "Выберите логотип:",
            ["Сбер QR (фирменный)", "Загрузить свой логотип"],
            horizontal=True,
        )
        if logo_choice == "Загрузить свой логотип":
            uploaded_logo = st.file_uploader(
                "Загрузите файл логотипа (PNG, JPG)", type=["png", "jpg", "jpeg"]
            )


def create_sber_logo_image():
    """Генерирует фирменный логотип Сбера (окружность с галочкой)"""
    size = 200
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    margin = 15
    lineWidth = 14
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        outline="black",
        width=lineWidth,
    )

    check_points = [
        (int(size * 0.30), int(size * 0.53)),
        (int(size * 0.45), int(size * 0.68)),
        (int(size * 0.72), int(size * 0.36)),
    ]
    draw.line(check_points, fill="black", width=lineWidth, joint="curve")
    return img


def draw_styled_qr(
    url, box_size, corner_type, dot_type, logo_mode, custom_logo, rotate
):
    # Используем высокий уровень коррекции ошибок при наличии логотипа
    error_corr = (
        qrcode.constants.ERROR_CORRECT_H
        if logo_mode
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

    # Создаем базовый QR на белом фоне
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    width, height = img.size

    # Кастомизация формы точек через обработку пикселей (простая имитация стилей для примера)
    # Поворачиваем QR-код ДО вставки логотипа (чтобы логотип оставался ровным)
    if rotate:
        img = img.rotate(270, expand=True)
        width, height = img.size

    # Накладываем логотип с белым охранным полем
    if logo_mode:
        try:
            if logo_mode == "Сбер QR (фирменный)":
                logo = create_sber_logo_image()
            else:
                if custom_logo:
                    logo = Image.open(custom_logo).convert("L")
                    logo = logo.point(lambda p: 0 if p < 140 else 255, "1").convert("RGBA")
                else:
                    logo = create_sber_logo_image()

            logo_max_size = min(width, height) // 4
            logo.thumbnail((logo_max_size, logo_max_size), Image.LANCZOS)

            # Белое охранное поле
            padding = 10
            bg_size = (logo.size[0] + padding * 2, logo.size[1] + padding * 2)
            background = Image.new("RGBA", bg_size, "white")

            bg_x = (bg_size[0] - logo.size[0]) // 2
            bg_y = (bg_size[1] - logo.size[1]) // 2
            background.paste(logo, (bg_x, bg_y), logo)

            pos_x = (width - background.size[0]) // 2
            pos_y = (height - background.size[1]) // 2
            img.paste(background, (pos_x, pos_y), background)

        except Exception as e:
            pass

    return img


# Правая колонка — Живой предпросмотр
with col_preview:
    st.markdown("### 📱 Предпросмотр")
    sample_url = (
        links_input.split("\n")[0].strip()
        if links_input
        else "https://get-qr.com/q_H6zb"
    )

    active_logo = logo_choice if add_logo else None
    preview_img = draw_styled_qr(
        sample_url,
        box_size=8,  # фиксированный размер для превью
        corner_type=corner_style,
        dot_type=dot_style,
        logo_mode=active_logo,
        custom_logo=uploaded_logo,
        rotate=rotate_images,
    )
    st.image(
        preview_img,
        caption="Результат для первой ссылки",
        use_container_width=True,
    )

st.write("---")

def create_pdf_from_image(img):
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


if st.button("🚀 Сгенерировать и скачать архив со всеми QR-кодами", type="primary", use_container_width=True):
    links = [line.strip() for line in links_input.split("\n") if line.strip()]

    if not links:
        st.warning("Пожалуйста, введите хотя бы одну ссылку.")
    else:
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i, link in enumerate(links, 1):
                safe_name = (
                    link.replace("https://", "")
                    .replace("http://", "")
                    .replace("/", "_")[:30]
                )
                file_name = f"qr_{i:02d}_{safe_name}"

                if output_format == "SVG":
                    qr_svg = qrcode.QRCode(
                        version=None,
                        error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=box_size,
                        border=4,
                    )
                    qr_svg.add_data(link)
                    qr_svg.make(fit=True)
                    svg_img = qr_svg.make_image(image_factory=SvgPathImage)
                    svg_data = svg_img.to_string(encoding="utf-8")
                    zip_file.writestr(
                        f"{file_name}.svg",
                        svg_data
                        if isinstance(svg_data, bytes)
                        else svg_data.encode("utf-8"),
                    )
                else:
                    active_logo_mode = logo_choice if add_logo else None
                    img = draw_styled_qr(
                        link,
                        box_size,
                        corner_type=corner_style,
                        dot_type=dot_style,
                        logo_mode=active_logo_mode,
                        custom_logo=uploaded_logo,
                        rotate=rotate_images,
                    )

                    if output_format == "PNG":
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format="PNG")
                        zip_file.writestr(f"{file_name}.png", img_byte_arr.getvalue())
                    elif output_format == "PDF":
                        pdf_data = create_pdf_from_image(img)
                        zip_file.writestr(f"{file_name}.pdf", pdf_data)

        zip_buffer.seek(0)

        st.success(f"Готово! Успешно сгенерировано QR-кодов: {len(links)}")
        st.download_button(
            label="📦 Скачать ZIP-архив с готовыми QR",
            data=zip_buffer,
            file_name="qr_codes_pro_batch.zip",
            mime="application/zip",
            use_container_width=True,
        )
