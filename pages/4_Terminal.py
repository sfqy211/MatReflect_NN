import streamlit as st
import subprocess
import os
import sys
import locale
import time

def submit_command():
    """Callback to handle input submission"""
    if st.session_state.cmd_input:
        st.session_state.new_command = st.session_state.cmd_input
        st.session_state.cmd_input = ""

def render_page():
    st.set_page_config(layout="wide", page_title="Terminal")
    
    st.title("网页终端 (Native Shell)")
    
    # Show current environment info
    current_env = os.environ.get('CONDA_DEFAULT_ENV', 'Unknown')
    python_path = sys.executable
    st.caption(f"当前环境: `{current_env}` | Python路径: `{python_path}`")
    
    st.info("此终端直接运行在宿主机的 Shell 环境中。支持 `cd` 命令切换目录。支持实时输出流 (用于编译/训练)。")

    # Initialize session state
    if 'cwd' not in st.session_state:
        st.session_state.cwd = os.getcwd()
    if 'terminal_history' not in st.session_state:
        st.session_state.terminal_history = []
    if 'new_command' not in st.session_state:
        st.session_state.new_command = None

    # Display current working directory
    st.write(f"**当前工作目录:** `{st.session_state.cwd}`")

    # Command Input
    st.text_input(
        "输入命令 (按回车执行):", 
        key="cmd_input", 
        on_change=submit_command
    )

    # Output Container
    output_container = st.empty()
    
    # Logic to process new command
    if st.session_state.new_command:
        command = st.session_state.new_command
        st.session_state.new_command = None  # Reset immediately
        
        # Add command to history
        st.session_state.terminal_history.append(f"$ {command}")
        
        # Handle 'cd' command
        if command.strip().startswith("cd "):
            try:
                parts = command.strip().split(" ", 1)
                if len(parts) > 1:
                    target_dir = parts[1]
                    # Handle relative paths
                    new_path = os.path.abspath(os.path.join(st.session_state.cwd, target_dir))
                    if os.path.exists(new_path) and os.path.isdir(new_path):
                        st.session_state.cwd = new_path
                        st.session_state.terminal_history.append(f"Changed directory to: {new_path}")
                    else:
                        st.session_state.terminal_history.append(f"Error: Directory not found: {target_dir}")
                else: # Just 'cd' goes to home or stays? Let's just stay or go to user home.
                     st.session_state.terminal_history.append(f"Current directory: {st.session_state.cwd}")

            except Exception as e:
                st.session_state.terminal_history.append(f"Error changing directory: {str(e)}")
            
        # Handle 'cls' or 'clear'
        elif command.strip().lower() in ['cls', 'clear']:
            st.session_state.terminal_history = []
            
        else:
            # Run generic command with streaming
            try:
                # Determine encoding
                system_encoding = locale.getpreferredencoding()
                
                process = subprocess.Popen(
                    command,
                    cwd=st.session_state.cwd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, # Merge stderr into stdout
                    stdin=subprocess.PIPE
                )
                
                # Stream output
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        try:
                            decoded_line = line.decode(system_encoding, errors='replace').rstrip()
                        except:
                            decoded_line = line.decode('utf-8', errors='replace').rstrip()
                        
                        if decoded_line:
                            st.session_state.terminal_history.append(decoded_line)
                            # Update UI incrementally
                            # Efficiently updating a large code block might be slow, but it's the simplest way in Streamlit
                            # We update the container with the FULL history so far
                            output_container.code("\n".join(st.session_state.terminal_history), language="bash")
                
                # Final check for any remaining output
                remaining_output, _ = process.communicate()
                if remaining_output:
                    try:
                        decoded = remaining_output.decode(system_encoding, errors='replace')
                    except:
                        decoded = remaining_output.decode('utf-8', errors='replace')
                    st.session_state.terminal_history.append(decoded)
                
            except Exception as e:
                st.session_state.terminal_history.append(f"Execution Error: {str(e)}")
        
        # Rerun to finalize state and ready for next input (optional, but helps clear any lag)
        st.rerun()

    # If not running a command, just show history
    if st.session_state.terminal_history:
        output_container.code("\n".join(st.session_state.terminal_history), language="bash")
        
        # Add clear button below history
        if st.button("清除日志"):
            st.session_state.terminal_history = []
            st.rerun()

render_page()
