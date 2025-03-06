from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich.panel import Panel
from rich.text import Text
import sys
import math
import json
import chess
import re
import io
import chess.pgn
import requests
from contextlib import redirect_stdout, redirect_stderr


def player_info(pgn):
    white_player = re.search(r'\[White\s+"([^"]+)"', pgn)
    black_player = re.search(r'\[Black\s+"([^"]+)"', pgn)
    white_rating = re.search(r'\[WhiteElo\s+"([^"]+)"', pgn)
    black_rating = re.search(r'\[BlackElo\s+"([^"]+)"', pgn)
    white_player = white_player.group(1) if white_player else "White"
    black_player = black_player.group(1) if black_player else "Black"
    white_rating = white_rating.group(1) if white_rating else "??"
    black_rating = black_rating.group(1) if black_rating else "??"

    info = {
        "white_player": white_player,"white_rating":  white_rating,"black_player":  black_player, "black_rating": black_rating
    }
    return info


def isBookMove(fen):
    board = chess.Board()
    board.set_fen(fen)
    fen = board.board_fen()
    openings = requests.get("https://daamin.hackclub.app/openings.json").json()
    for opening in openings:
        if (opening['fen']==fen):
            return [True, opening['name']]
    return [False]

def gradeMove(eval_change):
    if (eval_change>=4.5):
        return ("blunder")
    elif (eval_change>=2.6):
        return ("mistake")
    elif (eval_change>=1.3):
        return ("inaccuracy")
    elif (eval_change>=0.8):
        return ("good")
    elif (eval_change>=0.1):
        return ("excellent")
    else:
        return ("best_move")
    
def isBestMove(move_info):
    return (move_info['best_move'] ==  move_info['move'])

def classifyMoves(analysis):
    evalDiffs= [None]
    openings = ["Starting Position"]
    
    for counter in range(1, len(analysis)): 

        current = analysis[counter]
        previous = analysis[counter-1]

        current_type = current['eval']['type']
        previous_type = previous['eval']['type']
    
        book_move = isBookMove(current['fen'])

        if (book_move[0]):
            evalDiffs.append('book_move')
            openings.append(book_move[1])
        else: 
            openings.append(None)
            if (isBestMove(current)):
                evalDiffs.append('best_move')
            elif (current_type=='cp' and previous_type=='cp'):
                resp = cp_and_cp(current, previous)
                evalDiffs.append(resp)
            elif (current_type=='cp' and previous_type=='mate'):
                resp = cp_and_mate(current, previous)
                evalDiffs.append(resp)
            elif (current_type=='mate' and previous_type=='mate'):
                resp = mate_and_mate(current, previous)
                evalDiffs.append(resp)
            elif (current_type=='mate' and previous_type=='cp'):
                resp = mate_and_cp(current, previous)
                evalDiffs.append(resp)

    for counter, (move_type, opening) in enumerate(zip(evalDiffs, openings)):
        analysis[counter]['opening'] = opening
        analysis[counter]['move_type'] = move_type
    analysis = correctBookMoves(analysis)
    return analysis
    
def cp_and_cp(current, previous):
    diff = previous['eval']['value'] - current['eval']['value']
    diff = math.floor(diff*100)/100
    return gradeMove(abs(diff)) 

def cp_and_mate(current, previous):
    current_eval = current['eval']['value']
    if (current_eval >= 20):
        return ("excellent")
    elif (current_eval >= 12):
        return ("good")
    elif (current_eval >= 9):
        return ("inaccuracy")
    elif (current_eval>=6):
        return ("mistake")
    else:
        return ("blunder")    

def mate_and_cp(current, previous):
    previous_eval = previous['eval']['value']
    if (previous_eval >= 30):
        return ("good")
    elif (previous_eval >= 20):
        return ("inaccuracy")
    elif (previous_eval >= 10):
        return ("mistake")
    else:
        return ("blunder")

def mate_and_mate(current, previous):
    current_mate_in = current['eval']['value']
    previous_mate_in = previous['eval']['value']
    player_color = "b" if current['move_no']%2==0 else "w"
    match player_color:
        case "w":
            if (previous_mate_in > 0):
                if (current_mate_in > 0):
                    return ("excellent")
                elif (current_mate_in < 0):
                    return ("blunder")
            elif (previous_mate_in < 0):
                return ("excellent")
        case "b":
            if (previous_mate_in < 0):
                if (current_mate_in < 0):
                    return ("excellent")
                elif (current_mate_in > 0):
                    return ("blunder")
            elif (previous_mate_in > 0):
                return ("excellent")
            
def countMoveCategories(analysedFENs, pgn):
    move_types_b = []
    move_types_w = []
    for FEN in analysedFENs:
        if FEN['move_no']%2==0:
            move_types_b.append(FEN['move_type'])
        else:
            move_types_w.append(FEN['move_type'])
    accuracy = [(move_types_w.count('best_move') + move_types_w.count('best_move') + move_types_w.count('excellent'))/len(move_types_w), (move_types_b.count('best_move') + move_types_b.count('good') + move_types_b.count('excellent'))/(len(move_types_b)-1)]
    analysedFENs = {
        "info": player_info(pgn),
        "accuracy": {
            "white": math.floor(accuracy[0]*100*100)/100,
            "black": math.floor(accuracy[1]*100*100)/100,
        },
        "number_of_move_types": {
                "w":{
                    "best_move" : move_types_w.count('best_move'),
                    "excellent" : move_types_w.count('excellent'),
                    "good" : move_types_w.count('good'),
                    "inaccuracy" : move_types_w.count('inaccuracy'),
                    "mistake" : move_types_w.count('mistake'),
                    "blunder" : move_types_w.count('blunder'),
                    "book_move" : move_types_w.count('book_move'),
                },
                "b": {
                    "best_move" : move_types_b.count('best_move'),
                    "excellent" : move_types_b.count('excellent'),
                    "good" : move_types_b.count('good'),
                    "inaccuracy" : move_types_b.count('inaccuracy'),
                    "mistake" : move_types_b.count('mistake'),
                    "blunder" : move_types_b.count('blunder'),
                    "book_move" : move_types_b.count('book_move'),
                }
            },
        "move_evaluations": analysedFENs
    }
    return analysedFENs

def correctBookMoves(analysis):
    # this is an algorithm to add 'book_move' title to the missed FENs
    # in the openings list, not all FENs are mentioned
    # however if a move leads to a book-move
    # it is also a book move
    # this algo fills up those missing moves and it also makes the subsequent move to have the same opening-name
    opening = []
    
    for position in (analysis):
        # ? this makes a list of lists containg, move_no and opening name
        opening.append([position['move_no'], position['opening']])
    
    opening_reversed = []

    for x in range(len(opening)-1, 0, -1):
        # ! makes a list that is the reversal of the first one, this one doesnt include the starting position though
        opening_reversed.append(opening[x])
    
    index = None
    for move in opening_reversed:
        # * this gets the index of the last book_move
        if (move[1]):
            index = move[0]
            break

    if (index):
        # ? checks if there is any book move and then 
        # ! makes all moves a book move until that move
        for count, position in enumerate(opening):
            if (position[0] <= index and not position[1]):
                position[1] = opening[count-1][1]

    opening[0][1] = None

    for (position, individualOpening) in zip(analysis, opening):
        # this adds the new openings to the analysis and returns that variable
        if (individualOpening[1]):
            position['move_type'] = 'book_move'
            position['opening'] = individualOpening[1]


    for count, move in enumerate(analysis):
        if (not move['opening']):
            move['opening'] = analysis[count-1]['opening']


    return analysis



# the below function is used to check if the PGN format is correct or not
def checkPGNFormat(pgn):
    output = io.StringIO()
    with redirect_stdout(output), redirect_stderr(output):
        try:
            game = chess.pgn.read_game(io.StringIO(pgn))
        except Exception:
            pass
    console_output = output.getvalue().lower()
    if "illegal san:" in console_output or "illegal move" in console_output:
        return False
    else:
        game = chess.pgn.read_game(io.StringIO(pgn))
        gameString = str(game)
        if game is None:
            return False
        elif "1." not in gameString:
            return False
    return True


# the below function is used to check if the moves are legal or not
def validatePGN(pgn):
    if not checkPGNFormat(pgn):
        return False
    game = chess.pgn.read_game(io.StringIO(pgn))
    board = chess.Board()
    for move in game.mainline_moves():
        if board.is_legal(move):
            board.push(move)
        else:
            return False
    return True  


def changeFormat(pgn, infos, moves):
    game = chess.pgn.read_game(io.StringIO(pgn))
    board = game.board()
    default_fen = board.fen()
    for counter, (info, move) in enumerate(zip(infos, moves)):

        if (info['eval']['type']!='mate'):
            info['eval']['value']/=100
        if (not info['best_move']):
            info['best_move'] = (None)
        else:
            board.set_fen(infos[counter-1]['fen'])
            info['best_move'] = (board.san(chess.Move.from_uci(info['best_move'])))
            board.set_fen(default_fen)    
        info['move'] = move
    return infos

def review_game (pgn):
    game = chess.pgn.read_game(io.StringIO(pgn))
    board = game.board()
    moves = game.mainline_moves()
    moves_fens = [board.fen()]
    moves_san = [None]

    for move in moves:
        moves_san.append(board.san_and_push(move))
        moves_fens.append(board.fen())


    url="https://daamin.hackclub.app/api/engine"
    payload = {"fens": moves_fens}  
    response = requests.post(url, json=payload)
    analysis = response.json()
    analysis = changeFormat(pgn, analysis, moves_san)
    analysis = classifyMoves(analysis)
    analysis = countMoveCategories(analysis, pgn)
    return analysis


def main():
    if len(sys.argv) > 1:
        pgn_file= sys.argv[1]
        if pgn_file == "help":
            print("ChessMinal is a CLI - App that allows you to Review your chess games using their PGN.")
            print("Game Review is chess.com's paid (1 per day is free) feature that helps you to improve your chess skills and become a better player.")
            print("How to use: Visit github.com/daamin909/chessminal for a complete guide.")
            exit(0)
    else:
        pgn_file = input("Enter PGN's filepath: ")



    try:
        with open(pgn_file, "r") as f:
            pgn = f.read()
        validity = validatePGN(pgn)
    except:
        print("File Not Found: Enter a valid path and try again.")
        exit(0)

    if (validity):
        reviewed_game = review_game(pgn)
    else:
        print("Invalid PGN: Please try again.")
        exit(0)


    console = Console()
    chess_text = Text("""
    ▄████▄    ██░ ██ ▓    █████       ██████      ██████  
    ▒██▀ ▀█    ▓██░ ██▒    ▓█   ▀▒     ██    ▒     ▒██    
    ▒▓█    ▄   ▒██▀▀██░    ▒███  ░     ▓██▄  ░     ▓██▄  ░  
    ▒▓▓▄ ▄██▒  ░▓█ ░██     ▒▓█  ▄      ▒   ██▒     ▒   ██▒ 
    ▒ ▓███▀    ░░▓█▒░██    ▓░▒████▒    ██████▒▒    ██████▒                                          
    """, style="bold green")

    console.print(chess_text)


    console = Console()

    table = Table(title="", style="bold green", border_style="bright_blue")
    table.add_column("White Player", justify="center", style="bold white")
    table.add_column("White Rating", justify="center", style="bold yellow")
    table.add_column("Black Player", justify="center", style="bold white")
    table.add_column("Black Rating", justify="center", style="bold yellow")

    table.add_row(
        reviewed_game["info"]["white_player"],
        reviewed_game["info"]["white_rating"],
        reviewed_game["info"]["black_player"],
        reviewed_game["info"]["black_rating"]
    )

    console.print(table)

    console.print(Panel("Accuracy", style="bold magenta"))
    with Progress() as progress:
        task1 = progress.add_task("[bold white]White Accuracy", total=100)
        task2 = progress.add_task("[bold white]Black Accuracy", total=100)
        progress.update(task1, advance=reviewed_game["accuracy"]["white"])
        progress.update(task2, advance=reviewed_game["accuracy"]["black"])

    console.print(Panel("Move Types", style="bold blue"))

    move_types = Table(border_style="green")
    move_types.add_column("Player", justify="center")
    move_types.add_column("Best Move", justify="center")
    move_types.add_column("Excellent", justify="center")
    move_types.add_column("Good", justify="center")
    move_types.add_column("Inaccuracy", justify="center")
    move_types.add_column("Mistake", justify="center")
    move_types.add_column("Blunder", justify="center")
    move_types.add_column("Book Moves", justify="center")

    w_moves = reviewed_game["number_of_move_types"]["w"]
    b_moves = reviewed_game["number_of_move_types"]["b"]

    move_types.add_row(
        "White",
        str(w_moves["best_move"]),
        str(w_moves["excellent"]),
        str(w_moves["good"]),
        str(w_moves["inaccuracy"]),
        str(w_moves["mistake"]),
        str(w_moves["blunder"]),
        str(w_moves["book_move"])
    )

    move_types.add_row(
        "Black",
        str(b_moves["best_move"]),
        str(b_moves["excellent"]),
        str(b_moves["good"]),
        str(b_moves["inaccuracy"]),
        str(b_moves["mistake"]),
        str(b_moves["blunder"]),
        str(b_moves["book_move"])
    )

    console.print(move_types)
    console.print(Panel("Moves Analysis", style="bold yellow"))

    moves_table = Table(title="", show_header=True, header_style="bold green")
    moves_table.add_column("Move #", justify="center", style="bold cyan")
    moves_table.add_column("Move", justify="center", style="bold yellow")
    moves_table.add_column("Eval", justify="center", style="bold magenta")
    moves_table.add_column("Type", justify="center", style="bold red")

    moves_table.add_column("Move #", justify="center", style="bold cyan")
    moves_table.add_column("Move", justify="center", style="bold yellow")
    moves_table.add_column("Eval", justify="center", style="bold magenta")
    moves_table.add_column("Type", justify="center", style="bold red")

    for i in range(0, len(reviewed_game["move_evaluations"]), 2):
        move1 = reviewed_game["move_evaluations"][i]
        move2 = reviewed_game["move_evaluations"][i + 1] if i + 1 < len(reviewed_game["move_evaluations"]) else {"move_no": "-", "move": "-", "eval":{"value": "-"}, "move_type": "-"}
        
        moves_table.add_row(
            str(move1["move_no"]), move1["move"], str(move1["eval"]['value']), move1["move_type"],
            str(move2["move_no"]), move2["move"], str(move2["eval"]['value']), move2["move_type"]
        )
    console.print(moves_table)


if __name__ =="__main__":
    main()