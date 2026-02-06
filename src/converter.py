"""
Claude APIを使用したマークダウン変換モジュール
"""

import anthropic
import os
from pathlib import Path


def load_conversion_prompt() -> str:
    """変換プロンプトを読み込む"""
    prompt_path = Path(__file__).parent.parent / 'prompts' / 'conversion_prompt.txt'
    
    if prompt_path.exists():
        return prompt_path.read_text(encoding='utf-8')
    else:
        raise FileNotFoundError(f"変換プロンプトが見つかりません: {prompt_path}")


def convert_to_markdown(
    article_text: str,
    reporter_name: str = "",
    api_key: str = None,
) -> dict:
    """
    記事テキストをマークダウン形式に変換
    """
    api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        return {
            'success': False,
            'markdown': '',
            'error': 'ANTHROPIC_API_KEYが設定されていません'
        }
    
    try:
        system_prompt = load_conversion_prompt()
        
        user_message = f"""以下のWord原稿をマークダウン形式に変換してください。

【記者名】
{reporter_name if reporter_name else "（指定なし）"}

【原稿】
{article_text}

---

上記の原稿を、指示されたルールに従ってマークダウン形式に変換してください。
変換後のマークダウンのみを出力し、説明は不要です。"""

        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        markdown_result = message.content[0].text
        
        return {
            'success': True,
            'markdown': markdown_result,
            'error': None
        }
        
    except anthropic.APIError as e:
        return {
            'success': False,
            'markdown': '',
            'error': f'Claude API エラー: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'markdown': '',
            'error': f'変換エラー: {str(e)}'
        }


def proofread_article(
    markdown_text: str,
    api_key: str = None,
) -> dict:
    """
    マークダウン記事の校閲チェック
    """
    api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        return {
            'success': False,
            'report': '',
            'issues_count': 0,
            'error': 'ANTHROPIC_API_KEYが設定されていません'
        }
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        system_prompt = """あなたは日本語の校閲専門家です。
記事の校閲チェックを行い、以下の項目を確認してください：

1. 誤字・脱字
2. 漢字の誤用（同音異義語の誤り）
3. 送り仮名の揺れ
4. 全角英数字（半角に統一すべき箇所）
5. タグの閉じ忘れ（##タグ## と #### の対応）
6. 見出しの問題（同じパターンの連続、段落冒頭のコピー）

【重要】
- 原文は修正せず、指摘のみを行う
- 指摘は「（校閲：●●）」の形式で記載
- 問題がない場合は「校閲チェック完了：問題なし」と報告"""

        user_message = f"""以下のマークダウン記事を校閲チェックしてください。

{markdown_text}

---

校閲レポートを作成してください。
指摘がある場合は、該当箇所と指摘内容を明記してください。"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        report = message.content[0].text
        issues_count = report.count('校閲：') + report.count('指摘')
        
        return {
            'success': True,
            'report': report,
            'issues_count': issues_count,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'report': '',
            'issues_count': 0,
            'error': f'校閲エラー: {str(e)}'
        }
