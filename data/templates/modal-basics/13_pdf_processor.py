"""
13 - PDF 批量处理服务
业务场景：HR/财务部门需要批量处理大量 PDF 文档

解决的问题：
- 每月要处理数百份员工合同，需要添加公司水印
- 年终需要合并全年的财务报表为一个文件
- 本地处理大文件太慢，经常卡死

这个例子展示：
- 自定义 Image 安装 PDF 处理库
- 并行处理多个 PDF 文件
- PDF 合并、拆分、添加水印
- Volume 存储处理后的文件
"""
import modal
import io
from datetime import datetime

# 创建带有 PDF 处理库的自定义镜像
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "PyPDF2>=3.0.0",
    "reportlab>=4.0.0"
)

app = modal.App("pdf-processor", image=image)

# 存储处理后的 PDF
volume = modal.Volume.from_name("processed-pdfs", create_if_missing=True)


@app.function()
def add_watermark_to_pdf(pdf_data: bytes, watermark_text: str = "CONFIDENTIAL") -> bytes:
    """
    给 PDF 添加水印
    
    参数：
    - pdf_data: PDF 文件的二进制数据
    - watermark_text: 水印文字
    """
    from PyPDF2 import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import Color
    
    # 创建水印 PDF
    watermark_buffer = io.BytesIO()
    c = canvas.Canvas(watermark_buffer, pagesize=letter)
    
    # 设置水印样式
    c.setFont("Helvetica", 50)
    c.setFillColor(Color(0.5, 0.5, 0.5, alpha=0.3))  # 半透明灰色
    
    # 在页面中心绘制旋转的水印
    c.saveState()
    c.translate(300, 400)  # 移动到页面中心
    c.rotate(45)  # 旋转 45 度
    c.drawCentredString(0, 0, watermark_text)
    c.restoreState()
    
    c.save()
    watermark_buffer.seek(0)
    
    # 读取水印 PDF
    watermark_pdf = PdfReader(watermark_buffer)
    watermark_page = watermark_pdf.pages[0]
    
    # 读取原始 PDF
    input_pdf = PdfReader(io.BytesIO(pdf_data))
    output_pdf = PdfWriter()
    
    # 为每一页添加水印
    for page in input_pdf.pages:
        page.merge_page(watermark_page)
        output_pdf.add_page(page)
    
    # 输出结果
    output_buffer = io.BytesIO()
    output_pdf.write(output_buffer)
    return output_buffer.getvalue()


@app.function()
def merge_pdfs(pdf_list: list[bytes]) -> bytes:
    """
    合并多个 PDF 文件
    
    参数：
    - pdf_list: PDF 文件二进制数据的列表
    """
    from PyPDF2 import PdfReader, PdfWriter
    
    output_pdf = PdfWriter()
    
    for pdf_data in pdf_list:
        reader = PdfReader(io.BytesIO(pdf_data))
        for page in reader.pages:
            output_pdf.add_page(page)
    
    output_buffer = io.BytesIO()
    output_pdf.write(output_buffer)
    return output_buffer.getvalue()


@app.function()
def split_pdf(pdf_data: bytes, pages_per_split: int = 10) -> list[bytes]:
    """
    拆分 PDF 文件
    
    参数：
    - pdf_data: PDF 文件二进制数据
    - pages_per_split: 每个拆分文件的页数
    """
    from PyPDF2 import PdfReader, PdfWriter
    
    reader = PdfReader(io.BytesIO(pdf_data))
    total_pages = len(reader.pages)
    
    split_pdfs = []
    
    for start in range(0, total_pages, pages_per_split):
        writer = PdfWriter()
        end = min(start + pages_per_split, total_pages)
        
        for i in range(start, end):
            writer.add_page(reader.pages[i])
        
        buffer = io.BytesIO()
        writer.write(buffer)
        split_pdfs.append(buffer.getvalue())
    
    return split_pdfs


@app.function()
def extract_text_from_pdf(pdf_data: bytes) -> str:
    """
    从 PDF 提取文本
    
    参数：
    - pdf_data: PDF 文件二进制数据
    """
    from PyPDF2 import PdfReader
    
    reader = PdfReader(io.BytesIO(pdf_data))
    text_content = []
    
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        text_content.append(f"--- Page {i + 1} ---\n{text}")
    
    return "\n\n".join(text_content)


@app.function()
def get_pdf_info(pdf_data: bytes) -> dict:
    """
    获取 PDF 文件信息
    """
    from PyPDF2 import PdfReader
    
    reader = PdfReader(io.BytesIO(pdf_data))
    
    info = {
        "pages": len(reader.pages),
        "metadata": {}
    }
    
    if reader.metadata:
        for key in ["/Title", "/Author", "/Subject", "/Creator"]:
            if key in reader.metadata:
                info["metadata"][key.strip("/")] = reader.metadata[key]
    
    return info


@app.function()
def process_batch_pdfs(
    pdf_files: list[dict],  # [{"name": "file.pdf", "data": bytes, "operation": "watermark"}]
    watermark_text: str = "CONFIDENTIAL"
) -> list[dict]:
    """
    批量处理多个 PDF 文件
    """
    results = []
    
    for pdf_file in pdf_files:
        try:
            operation = pdf_file.get("operation", "watermark")
            
            if operation == "watermark":
                processed_data = add_watermark_to_pdf.remote(
                    pdf_file["data"],
                    watermark_text
                )
            elif operation == "extract_text":
                text = extract_text_from_pdf.remote(pdf_file["data"])
                results.append({
                    "name": pdf_file["name"],
                    "status": "success",
                    "operation": operation,
                    "text": text
                })
                continue
            else:
                processed_data = pdf_file["data"]
            
            results.append({
                "name": pdf_file["name"],
                "status": "success",
                "operation": operation,
                "data": processed_data
            })
        except Exception as e:
            results.append({
                "name": pdf_file["name"],
                "status": "error",
                "error": str(e)
            })
    
    return results


@app.function(volumes={"/output": volume})
def save_processed_pdfs(processed_files: list[dict], folder_name: str = "batch") -> list[str]:
    """
    保存处理后的 PDF 到 Volume
    """
    saved_paths = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for pdf_file in processed_files:
        if pdf_file["status"] == "success" and "data" in pdf_file:
            filename = f"/output/{folder_name}/{timestamp}_{pdf_file['name']}"
            
            # 确保目录存在
            import os
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, "wb") as f:
                f.write(pdf_file["data"])
            saved_paths.append(filename)
    
    volume.commit()
    return saved_paths


def create_sample_pdf(title: str, pages: int = 3) -> bytes:
    """
    创建示例 PDF 文件（用于演示）
    """
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    for i in range(pages):
        c.setFont("Helvetica-Bold", 24)
        c.drawString(100, 700, f"{title}")
        c.setFont("Helvetica", 14)
        c.drawString(100, 650, f"Page {i + 1} of {pages}")
        c.drawString(100, 620, "This is a sample PDF document for demonstration.")
        c.drawString(100, 590, f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 添加一些填充内容
        y = 550
        for j in range(10):
            c.drawString(100, y, f"Sample content line {j + 1}: Lorem ipsum dolor sit amet...")
            y -= 20
        
        c.showPage()
    
    c.save()
    return buffer.getvalue()


@app.local_entrypoint()
def main():
    """
    演示 PDF 批量处理
    
    使用方法：
    - 运行演示：modal run 13_pdf_processor.py
    """
    print("📄 PDF 批量处理服务")
    print("=" * 50)
    
    # 创建示例 PDF 文件
    print("\n📝 创建示例 PDF 文件...")
    sample_pdfs = []
    for i in range(5):
        pdf_data = create_sample_pdf(f"Document {i + 1}", pages=3)
        sample_pdfs.append({
            "name": f"document_{i + 1}.pdf",
            "data": pdf_data,
            "operation": "watermark"
        })
        print(f"  ✓ 创建 document_{i + 1}.pdf (3 页)")
    
    # 批量添加水印
    print(f"\n🔄 批量添加水印中...")
    processed = process_batch_pdfs.remote(sample_pdfs, "© 2024 公司机密")
    
    success_count = sum(1 for p in processed if p["status"] == "success")
    print(f"✅ 处理完成: {success_count}/{len(sample_pdfs)} 成功")
    
    # 保存到 Volume
    print("\n💾 保存处理后的文件...")
    saved_paths = save_processed_pdfs.remote(processed, "watermarked")
    print(f"   已保存 {len(saved_paths)} 个文件")
    
    # 演示合并 PDF
    print("\n📎 演示 PDF 合并...")
    pdf_data_list = [p["data"] for p in processed if p["status"] == "success"][:3]
    merged_pdf = merge_pdfs.remote(pdf_data_list)
    merged_info = get_pdf_info.remote(merged_pdf)
    print(f"   合并后共 {merged_info['pages']} 页")
    
    # 演示拆分 PDF
    print("\n✂️  演示 PDF 拆分...")
    split_pdfs = split_pdf.remote(merged_pdf, pages_per_split=3)
    print(f"   拆分为 {len(split_pdfs)} 个文件")
    
    # 演示文本提取
    print("\n📖 演示文本提取...")
    text = extract_text_from_pdf.remote(sample_pdfs[0]["data"])
    print(f"   提取文本预览: {text[:100]}...")
    
    print("\n" + "=" * 50)
    print("💡 提示:")
    print("1. add_watermark_to_pdf: 添加水印")
    print("2. merge_pdfs: 合并多个 PDF")
    print("3. split_pdf: 拆分 PDF")
    print("4. extract_text_from_pdf: 提取文本")
    print("5. process_batch_pdfs: 批量处理")

