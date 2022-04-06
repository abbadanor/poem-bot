from transformers import AutoTokenizer, AutoModelForCausalLM
import os

if os.path.isdir('./model'):
    print('You have already downloaded the model.')
else:
    tokenizer = AutoTokenizer.from_pretrained("birgermoell/swedish-gpt")
    model = AutoModelForCausalLM.from_pretrained("birgermoell/swedish-gpt", pad_token_id=tokenizer.eos_token_id)
    tokenizer.save_pretrained("./model")
    model.save_pretrained("./model")
