import os
import random
import google.generativeai as genai
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure Gemini AI
genai.configure(api_key='YOUR_API_KEY')  # Replace with your actual API key
model = genai.GenerativeModel('models/gemini-2.0-flash-exp')

def init_game():
    """Initialize a new game board."""
    return [[" " for _ in range(3)] for _ in range(3)]

def is_winner(board, player):
    """Check if the given player has won the game."""
    # Check rows
    for row in board:
        if all(cell == player for cell in row):
            return True
    
    # Check columns
    for col in range(3):
        if all(board[row][col] == player for row in range(3)):
            return True
    
    # Check diagonals
    if all(board[i][i] == player for i in range(3)) or \
       all(board[i][2-i] == player for i in range(3)):
        return True
    
    return False

def is_draw(board):
    """Check if the game is a draw."""
    return all(cell != " " for row in board for cell in row)

def get_ai_move(board):
    """Get AI's move using improved strategy with Gemini AI as fallback."""
    # First, check if AI can win in the next move
    for i in range(9):
        row, col = divmod(i, 3)
        if board[row][col] == " ":
            board[row][col] = "O"
            if is_winner(board, "O"):
                board[row][col] = " "  # Reset the test move
                return i + 1
            board[row][col] = " "

    # Then, block player's winning move
    for i in range(9):
        row, col = divmod(i, 3)
        if board[row][col] == " ":
            board[row][col] = "X"
            if is_winner(board, "X"):
                board[row][col] = " "  # Reset the test move
                return i + 1
            board[row][col] = " "

    # Try to get a strategic move from Gemini AI
    try:
        board_str = "\n".join([" | ".join(row) for row in board])
        prompt = f"""
        You are playing Tic-Tac-Toe as O. 
        Choose a strategic move from 1-9.
        Current board:
        {board_str}
        Board positions:
        1 | 2 | 3
        ---------
        4 | 5 | 6
        ---------
        7 | 8 | 9
        Respond only with the number of an available move.
        """
        
        response = model.generate_content(prompt)
        move_str = response.text.strip()
        
        if move_str.isdigit():
            move = int(move_str)
            row, col = divmod(move - 1, 3)
            if 0 <= move - 1 < 9 and board[row][col] == " ":
                return move
    except Exception as e:
        print(f"Gemini AI error: {e}")

    print('fuck1')

    # Fallback to strategic position selection
    # Prefer center, then corners, then sides
    preferred_moves = [5, 1, 3, 7, 9, 2, 4, 6, 8]  # Center, corners, sides
    for move in preferred_moves:
        row, col = divmod(move - 1, 3)
        if board[row][col] == " ":
            return move

    # Final fallback to any available move
    available_moves = [i for i in range(1, 10) if board[(i-1)//3][(i-1)%3] == " "]
    return random.choice(available_moves) if available_moves else None

@app.route('/')
def index():
    """Initialize or reset the game."""
    session['board'] = init_game()
    return render_template('board.html', board=_prepare_board_with_moves(session['board']))

@app.route('/move', methods=['POST'])
def make_move():
    """Handle player moves and AI response."""
    board = session.get('board', init_game())
    
    try:
        move = int(request.form.get('move')) - 1
        row, col = divmod(move, 3)
        
        # Validate player move
        if 0 <= move < 9 and board[row][col] == " ":
            # Make player's move
            board[row][col] = "X"
            session['board'] = board
            
            # Check player win
            if is_winner(board, "X"):
                return redirect(url_for('game_over', result='player'))
            
            # Check draw
            if is_draw(board):
                return redirect(url_for('game_over', result='draw'))
            
            # AI's turn
            ai_move = get_ai_move(board)
            if ai_move:
                ai_row, ai_col = divmod(ai_move - 1, 3)
                board[ai_row][ai_col] = "O"
                session['board'] = board
                
                # Check AI win
                if is_winner(board, "O"):
                    return redirect(url_for('game_over', result='ai'))
                
                # Check draw after AI move
                if is_draw(board):
                    return redirect(url_for('game_over', result='draw'))
    
    except (ValueError, TypeError):
        # Handle invalid moves silently
        pass
    
    return render_template('board.html', board=_prepare_board_with_moves(board))

def _prepare_board_with_moves(board):
    """Prepare board with move numbers for rendering."""
    return [
        [{'value': cell, 'move_num': i*3 + j + 1} for j, cell in enumerate(row)]
        for i, row in enumerate(board)
    ]

@app.route('/game_over/<result>')
def game_over(result):
    """Game over route to display result."""
    return render_template('game_over.html', result=result)

@app.route('/restart')
def restart():
    """Restart the game route."""
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)