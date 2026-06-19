from openai import OpenAI

client = OpenAI(
    base_url='https://llm.liaufms.org/v1/qwen2-5-14b-instruct-awq',
    api_key='REIkURcI7rTTqsTwlJi8MrgnKFwOiqky7Ezh7hH-l-k'
)

def perguntar(mensagens: list) -> str:
    resp = client.chat.completions.create(
        model='Qwen/Qwen2.5-14B-Instruct-AWQ',
        messages=mensagens,
    )
    return resp.choices[0].message.content