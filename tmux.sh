#!/bin/env sh

# Define the session name
sess="tmux-session"

# Check if the session exists
if tmux has-session -t "$sess" 2>/dev/null; then
	echo "Session $sess already exists. Attaching to it."
	tmux attach -t "$sess"
else
	# If the session doesn't exist, create it
	echo "Creating and attaching to session $sess."
	tmux new-session -d -s "$sess"
	tmux send-keys -t "$sess" "cd vwap_options" C-m
	tmux send-keys -t "$sess" "pwd" C-m
	tmux send-keys -t "$sess" "python3 main.py" C-m
	tmux attach -t "$sess"
fi
