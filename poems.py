from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from enum import IntEnum
import threading
import itertools
import random
import curses
import time
import re

class Screen(IntEnum):
    WELCOME = 1
    SETUP = 2
    POEM = 3

def draw_screen(stdscr: 'curses._CursesWindow'):
    def add_centered_str(str, y_offset=0, str_length=None):
        start_y = int((height // 2) - 2)
        if str_length:
            start_x = int((width // 2) - (str_length // 2) - str_length % 2)
            stdscr.addstr(start_y + y_offset, start_x, str.ljust(str_length))
        else:
            start_x = int((width // 2) - (len(str) // 2) - len(str) % 2)
            stdscr.addstr(start_y + y_offset, start_x, str)

    def display_loading_animation():
        for c in itertools.cycle(['=----', '-=---', '--=--', '---=-', '----=', '---=-','--=--','-=---']):
            # break if generator loaded
            if generator:
                break
            add_centered_str(f'[{c}]', 1)
            stdscr.refresh()
            time.sleep(0.1)
        
    questions = {
'Hur många rader vill du ha din dikt?': {'name':'poem_line_count','selection':0, 'opts':{'2':2, '3':3, '4':4, '5':5}},
        'Vilket tema vill du att den ska handla om?': {'name':'poem_introductions', 'selection':0, 'opts':{'Havet':['Havet är'], 'Naturen':['Genom dalens stilla', 'Regnet smattrar'], 'Filosofi':['Världens oskuld vilar', 'Ljuv är', 'Sällan är dagen']}}
    }

    k = 0
    question_index = 0
    generator = None
    screen = Screen.WELCOME

    # clear and refresh for blank canvas
    stdscr.clear()
    stdscr.refresh()
    height, width = stdscr.getmaxyx()

    # use transparent background
    curses.use_default_colors()
    curses.curs_set(0)

    # Start colors in curses
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

    add_centered_str('Loading pipeline')
    loading_thread = threading.Thread(target=display_loading_animation)
    loading_thread.start()

    tokenizer = AutoTokenizer.from_pretrained("./model")
    model = AutoModelForCausalLM.from_pretrained("./model", pad_token_id=tokenizer.eos_token_id)
    generator = pipeline('text-generation', model=model, tokenizer=tokenizer)
    while (k != ord('q')):
        # Initialization
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        if screen == Screen.WELCOME:
            stdscr.attron(curses.color_pair(2))
            stdscr.attron(curses.A_BOLD)

            add_centered_str('Poem Creator',-1)

            stdscr.attroff(curses.color_pair(2))
            stdscr.attroff(curses.A_BOLD)

            add_centered_str('v0.0.1')
            add_centered_str('Press any key to continue...', 2)

            if k != 0:
                screen = Screen.SETUP
                k = 0
                continue

        elif screen == Screen.SETUP:
            max_question_length = 0
            for q in questions:
                if len(q) > max_question_length:
                    max_question_length = len(q)

            # accounting for this -> (1/2)
            max_question_length += 6
            
            add_centered_str(f'({question_index + 1}/{str(len(questions))}) {list(questions)[question_index]}', -2, max_question_length)
            for i, answer in enumerate(list(questions.values())[question_index]['opts']):
                if i == list(questions.values())[question_index]['selection']:
                    stdscr.attron(curses.color_pair(3))
                    add_centered_str(answer, i, max_question_length)
                    stdscr.attroff(curses.color_pair(3))
                else:
                    add_centered_str(answer, i, max_question_length)

            # forward (enter key)
            if (k == 10 or k == ord('l')):
                if question_index < len(questions) - 1:
                    question_index += 1
                else:
                    screen = Screen.POEM
                k = 0
                continue

            # backward
            if k == ord('h') and question_index > 0:
                question_index -= 1
                k = 0
                continue

            # up
            if k == ord('k') and list(questions.values())[question_index]['selection'] > 0:
                list(questions.values())[question_index]['selection'] -= 1
                k = 0
                continue

            # down
            if k == ord('j') and list(questions.values())[question_index]['selection'] < len(list(questions.values())[question_index]['opts']) - 1:
                list(questions.values())[question_index]['selection'] += 1
                k = 0
                continue
        else:
            poem_line_count = list(list(questions.values())[0]['opts'].values())[list(questions.values())[0]['selection']]
            poem_introductions = list(list(questions.values())[1]['opts'].values())[list(questions.values())[1]['selection']]
            conjunctions = ['och']
            poem_length = 12
            length_increment = 10

            def cleanPoem(poem):
                # tar bort äckel päckel
                if re.search(r"([\s.!?\.,'])\1+", poem):
                    for x in re.finditer(r"([\s.!?\.,'])\1+", poem):
                        poem = poem.replace(x.group(), x.group(1))
                # den tar bort den sista biten av en sträng efter skiljetecken (.?!)
                if re.findall(r'\.|\?|!', poem):
                    return " ".join(re.split(r'(?<=[\.\!\?])\s*', poem)[:-1])
                # om inga avgränsare finns men kommatecken finns, ta bort sista biten av sträng efter kommatecken
                elif ',' in poem:
                    return ",".join(poem.split(',')[:-1]) + ','
                # om inga skiljetecken finns, ta strängen fram tills första konjunktion
                else:
                    poem_conjunctions = []
                    for c in conjunctions:
                        for match in re.finditer(f" {c} | {c}$", poem):
                            poem_conjunctions.append(match.span()[0])
                    if not poem_conjunctions:
                        return False
                    else:
                        return poem[:poem_conjunctions[-1]] + '.'


            def generatePoem(length, input_poem=''):
                if input_poem:
                    poem = generator(input_poem, max_length=length)[0]['generated_text']
                    poem = poem.replace(input_poem, '').strip()
                else:
                    poem = generator(random.choice(poem_introductions), max_length=length)[0]['generated_text']
                poem = cleanPoem(poem)
                if poem is None or poem is False:
                    return generatePoem(length, input_poem)
                else:
                    return poem
            poems = []
        
            for i in range(poem_line_count):
                poem = generatePoem(poem_length, " ".join(poems))
                if i == (poem_line_count - 1):
                    poem = poem.replace(',', '.')
                poems.append(poem)
                poem_length += length_increment
            max_poem_length = 0
            for p in poems:
                if len(p) > max_poem_length:
                    max_poem_length = len(p)
            for i, poem in enumerate(poems):
                add_centered_str(poem, i, max_poem_length)

        stdscr.refresh()
        k = stdscr.getch()

def main():
    curses.wrapper(draw_screen)

if __name__ == "__main__":
    main()
