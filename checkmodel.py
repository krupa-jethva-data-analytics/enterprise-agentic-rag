from groq import Groq
from app.config import Settings

client = Groq(api_key=Settings.GROQ_API_KEY)

models = client.models.list()

print("\nModels available to your API key:\n")

for model in models.data:
    print(model.id)