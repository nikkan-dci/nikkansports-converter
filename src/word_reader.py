"""
Word文書読み込みモジュール
"""

from docx import Document
from docx.shared import Inches
import io
from typing import Optional


def read_word_file(file_bytes: bytes) -> dict:
    """
    Wordファイルを読み込み、構造化データを返す
    
    Args:
        file_bytes: Wordファイルのバイトデータ
        
    Returns:
        dict: 抽出されたデータ
            - full_text: 全文テキスト
            - paragraphs: 段落リスト
            - has_images: 画像があるか
            - image_count: 画像数（推定）
    """
    doc = Document(io.BytesIO(file_bytes))
    
    paragraphs = []
    full_text_parts = []
    image_count = 0
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append({
                'text': text,
                'style': para.style.name if para.style else 'Normal',
                'is_bold': any(run.bold for run in para.runs if run.bold),
            })
            full_text_parts.append(text)
        
        # 画像の検出（インライン画像）
        for run in para.runs:
            if run._element.xpath('.//a:blip'):
                image_count += 1
    
    # 文書内の画像を追加でカウント
    for rel in doc.part.rels.values():
        if "image" in rel.target_ref:
            image_count += 1
    
    # 重複を除去（大まかな推定値）
    image_count = max(1, image_count // 2) if image_count > 0 else 0
    
    return {
        'full_text': '\n\n'.join(full_text_parts),
        'paragraphs': paragraphs,
        'has_images': image_count > 0,
        'image_count': image_count,
    }


def extract_text_only(file_bytes: bytes) -> str:
    """
    Wordファイルからテキストのみを抽出
    
    Args:
        file_bytes: Wordファイルのバイトデータ
        
    Returns:
        str: 抽出されたテキスト
    """
    doc = Document(io.BytesIO(file_bytes))
    
    text_parts = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            text_parts.append(text)
    
    return '\n\n'.join(text_parts)
