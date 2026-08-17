import anthropic 
import json


input_file = 'selected_players_lp.json'

with open(input_file,'r',encoding='utf-8') as file:
    squad = json.load(file)

client = anthropic.Anthropic()

message = client.messages.create(model='claude-sonnet-5',
                                 max_tokens=2000,
                                 thinking = {'type':'disabled'},
                                 messages=[{
                                     "role": "user",
                                     "content": f"A linear programming solver selected this football squd: {squad}."
                                     "Explain in plain, everyday language why these players were chosen as if explaining \
                                     to a non-technical person with no background in math or optimization. Do not use mathematical \
                                     equations, technical jargons. Focus on the practical story: budget tradeoffs, positional balance, and value for money.\
                                     And also does not use unrelated analogies like 'selecting top chefs' or anything like that. everyone knows the football.\
                                     but may be you could explain why messi was chosen for CAM role not his typical RW role."
                                 }])


for block in message.content:
    print(block.type)
    if block.type == 'text':
        with open('squad_1_explanation.txt','w',encoding='utf-8') as f:
            f.write(block.text)