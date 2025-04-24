

async def remove_backticks(input_str):
    if input_str.endswith("\n```"):
        input_str = input_str[:-4]  # Remove ending backticks
    if input_str.startswith("```\n"):
        input_str = input_str[4:]  # Remove starting backticks
    return input_str