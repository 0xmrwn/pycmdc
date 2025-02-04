from InquirerPy.utils import get_style


def get_custom_style():
    """Centralized style configuration for all InquirerPy prompts"""
    return get_style(
        {
            "questionmark": "#ff9d00 bold",
            "answermark": "#00ff00 bold",
            "question": "bold",
            "answered_question": "#BFBFBF bold",
            "answer": "#5F87FF",
            "input": "#18ac91",
            "pointer": "#FFA500",
            "checkbox": "#98c379",
            "fuzzy_border": "#4C9DF3",
            "fuzzy_match": "#c678dd",
            "fuzzy_prompt": "#61afef",
            "fuzzy_info": "#18ac91 bold",
        },
        style_override=False,  # Merge with default style
    )
