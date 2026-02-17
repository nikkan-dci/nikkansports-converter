# -*- coding: utf-8 -*-
"""
日刊スポーツ記事変換モジュール
マークダウン変換と一問一答変換の両方に対応
"""

import anthropic
import os
import re


def load_conversion_prompt():
    """マークダウン変換用プロンプトを読み込む"""
    prompt_path = "prompts/conversion_prompt.txt"
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def load_qa_prompt():
    """一問一答変換用プロンプトを読み込む"""
    prompt_path = "prompts/qa_prompt.txt"
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def convert_to_markdown(article_text: str, api_key: str, reporter_name: str = "") -> dict:
    """
    記事テキストをマークダウン形式に変換する
    
    Args:
        article_text: 変換する記事テキスト
        api_key: Anthropic APIキー
        reporter_name: 記者名（オプション）
    
    Returns:
        変換結果の辞書 {'success': bool, 'markdown': str, 'error': str}
    """
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        conversion_rules = load_conversion_prompt()
        
        # 記者名がある場合は追加指示
        reporter_instruction = ""
        if reporter_name:
            reporter_instruction = f"\n\n【記者名】\n記事末尾に「【{reporter_name}】」を配置してください。"
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            messages=[
                {
                    "role": "user",
                    "content": f"""以下の変換ルールに従って、記事をマークダウン形式に変換してください。

【変換ルール】
{conversion_rules}
{reporter_instruction}

【変換する記事】
{article_text}

変換後のマークダウンのみを出力してください。説明は不要です。"""
                }
            ]
        )
        
        return {
            'success': True,
            'markdown': message.content[0].text,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'markdown': None,
            'error': str(e)
        }


def convert_to_qa(article_text: str, api_key: str) -> dict:
    """
    音声文字起こしテキストを一問一答形式に変換する
    
    Args:
        article_text: 変換する文字起こしテキスト
        api_key: Anthropic APIキー
    
    Returns:
        変換結果の辞書 {'success': bool, 'qa_text': str, 'error': str}
    """
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        qa_rules = load_qa_prompt()
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            messages=[
                {
                    "role": "user",
                    "content": f"""以下の変換ルールに従って、音声文字起こしを一問一答形式に変換してください。

【変換ルール】
{qa_rules}

【変換する文字起こし】
{article_text}

変換後の一問一答形式のみを出力してください。説明は不要です。"""
                }
            ]
        )
        
        return {
            'success': True,
            'qa_text': message.content[0].text,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'qa_text': None,
            'error': str(e)
        }


def proofread_article(markdown_text: str, api_key: str) -> dict:
    """
    マークダウン変換後の記事を校閲する
    
    Args:
        markdown_text: 校閲する変換済みテキスト
        api_key: Anthropic APIキー
    
    Returns:
        校閲結果の辞書 {'success': bool, 'report': str, 'issues_count': int, 'error': str}
    """
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": f"""以下のマークダウン変換済み記事を校閲してください。

【校閲チェック項目】
1. 誤字・脱字
2. 漢字の誤用（同音異義語の誤りなど）
3. 送り仮名の揺れ
4. 全角英数字（半角に統一すべき箇所）
5. タグの閉じ忘れ（####の不足など）
6. 見出しの問題（500文字ルール違反、パターンの連続など）

【重要】
- 原文は絶対にそのまま残す
- 指摘箇所の直後に (校閲:●●) を追加するのみ
- 問題がない場合は「校閲チェック完了：問題は見つかりませんでした」と出力

【校閲する記事】
{markdown_text}

校閲結果を出力してください。"""
                }
            ]
        )
        
        report = message.content[0].text
        
        # 指摘件数をカウント（「校閲:」の出現回数）
        issues_count = len(re.findall(r'校閲[:：]', report))
        
        return {
            'success': True,
            'report': report,
            'issues_count': issues_count,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'report': None,
            'issues_count': 0,
            'error': str(e)
        }


def proofread_qa(qa_text: str, api_key: str) -> dict:
    """
    一問一答変換後のテキストを校閲する
    
    Args:
        qa_text: 校閲する変換済みテキスト
        api_key: Anthropic APIキー
    
    Returns:
        校閲結果の辞書 {'success': bool, 'report': str, 'issues_count': int, 'error': str}
    """
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": f"""以下の一問一答変換済みテキストを校閲してください。

【校閲チェック項目】
1. 誤字・脱字
2. 漢字の誤用（同音異義語の誤りなど）
3. 送り仮名の揺れ

【重要】
- 原文は絶対にそのまま残す
- 指摘箇所の直後に (校閲:●●) を追加するのみ
- 問題がない場合は「校閲チェック完了：問題は見つかりませんでした」と出力

【校閲するテキスト】
{qa_text}

校閲結果を出力してください。"""
                }
            ]
        )
        
        report = message.content[0].text
        
        # 指摘件数をカウント（「校閲:」の出現回数）
        issues_count = len(re.findall(r'校閲[:：]', report))
        
        return {
            'success': True,
            'report': report,
            'issues_count': issues_count,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'report': None,
            'issues_count': 0,
            'error': str(e)
        }


def revise_markdown(markdown_text: str, revision_request: str, api_key: str) -> dict:
    """
    マークダウン変換後の記事に修正リクエストを適用する
    
    Args:
        markdown_text: 修正する変換済みテキスト
        revision_request: 修正リクエスト内容
        api_key: Anthropic APIキー
    
    Returns:
        修正結果の辞書 {'success': bool, 'markdown': str, 'error': str}
    """
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            messages=[
                {
                    "role": "user",
                    "content": f"""以下のマークダウン変換済み記事に対して、修正リクエストを適用してください。

【現在の記事】
{markdown_text}

【修正リクエスト】
{revision_request}

【重要】
- 修正リクエストに該当する箇所のみを修正
- それ以外の部分は変更しない
- 原稿本文の内容（発言内容など）は絶対に修正しない

修正後の全文を出力してください。説明は不要です。"""
                }
            ]
        )
        
        return {
            'success': True,
            'markdown': message.content[0].text,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'markdown': None,
            'error': str(e)
        }


def revise_qa(qa_text: str, revision_request: str, api_key: str) -> dict:
    """
    一問一答変換後のテキストに修正リクエストを適用する
    
    Args:
        qa_text: 修正する変換済みテキスト
        revision_request: 修正リクエスト内容
        api_key: Anthropic APIキー
    
    Returns:
        修正結果の辞書 {'success': bool, 'qa_text': str, 'error': str}
    """
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            messages=[
                {
                    "role": "user",
                    "content": f"""以下の一問一答変換済みテキストに対して、修正リクエストを適用してください。

【現在のテキスト】
{qa_text}

【修正リクエスト】
{revision_request}

【重要】
- 修正リクエストに該当する箇所のみを修正
- それ以外の部分は変更しない
- 回答部分の発言内容は絶対に修正しない

修正後の全文を出力してください。説明は不要です。"""
                }
            ]
        )
        
        return {
            'success': True,
            'qa_text': message.content[0].text,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'qa_text': None,
            'error': str(e)
        }
