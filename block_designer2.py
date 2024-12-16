import tkinter as tk
from tkinter import simpledialog, filedialog
import json
#from PIL import ImageGrab

class DigitalDesignApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Digital Design Tool")

        # Canvas for drawing
        self.canvas = tk.Canvas(root, width=800, height=600, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bind events for interaction
        self.canvas.bind("<Button-3>", self.open_block_popup)  # Right-click for adding blocks
        self.canvas.bind("<Button-1>", self.start_action)
        self.canvas.bind("<B1-Motion>", self.drag_block)
        self.canvas.bind("<ButtonRelease-1>", self.complete_action)
        self.canvas.bind("<Motion>", self.highlight_port)

        # Data storage
        self.blocks = []  # List of blocks with their properties
        self.connections = []  # List of connections
        self.temp_line = None  # Temporary line for connecting

        self.start_port = None  # Start port for a connection
        self.selected_block = None  # Block currently being dragged
        self.history = []  # For undo/redo functionality
        self.redo_stack = []

        # Menu for save, load, and export
        self.create_menu()

    def create_menu(self):
        """Create a menu for saving, loading, and exporting."""
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)

        file_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Design", command=self.save_design)
        file_menu.add_command(label="Load Design", command=self.load_design)
        #file_menu.add_command(label="Export as Image", command=self.export_as_image)

        edit_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=self.undo)
        edit_menu.add_command(label="Redo", command=self.redo)

    def open_block_popup(self, event):
        """Open a popup to configure a new block."""
        x, y = event.x, event.y
        popup = tk.Toplevel(self.root)
        popup.title("Add Block")
        popup.geometry("200x150")

        # Number of inputs
        tk.Label(popup, text="Number of Inputs:").pack()
        inputs_var = tk.IntVar(value=1)
        tk.Entry(popup, textvariable=inputs_var).pack()

        # Number of outputs
        tk.Label(popup, text="Number of Outputs:").pack()
        outputs_var = tk.IntVar(value=1)
        tk.Entry(popup, textvariable=outputs_var).pack()

        # Submit button
        def submit():
            num_inputs = inputs_var.get()
            num_outputs = outputs_var.get()
            popup.destroy()
            self.create_block(x, y, num_inputs, num_outputs)

        tk.Button(popup, text="Add Block", command=submit).pack()

    def create_block(self, x, y, num_inputs, num_outputs):
        """Create a new block at the specified position."""
        block_width = 100
        block_height = 50 + max(num_inputs, num_outputs) * 10

        # Draw the block
        rect = self.canvas.create_rectangle(x, y, x + block_width, y + block_height, fill="lightblue")
        text = self.canvas.create_text(x + block_width / 2, y + block_height / 2, text=f"Block {len(self.blocks)}")

        # Draw input ports
        inputs = []
        for i in range(num_inputs):
            port_y = y + 20 + i * 10
            port = self.canvas.create_oval(x - 5, port_y - 5, x + 5, port_y + 5, fill="red", tags="port")
            inputs.append(port)

        # Draw output ports
        outputs = []
        for i in range(num_outputs):
            port_y = y + 20 + i * 10
            port = self.canvas.create_oval(x + block_width - 5, port_y - 5, x + block_width + 5, port_y + 5, fill="green", tags="port")
            outputs.append(port)

        # Save block details
        block = {
            "rect": rect,
            "text": text,
            "inputs": inputs,
            "outputs": outputs,
            "x": x,
            "y": y,
            "num_inputs": num_inputs,
            "num_outputs": num_outputs
        }
        self.blocks.append(block)
        self.history.append(("add_block", block))
        self.redo_stack.clear()

    def start_action(self, event):
        """Start either a connection or block movement."""
        clicked_port = self.get_port_at(event.x, event.y)
        if clicked_port:
            # Start a connection
            self.start_port = clicked_port
            # Draw a temporary line for visual feedback
            start_coords = self.canvas.coords(clicked_port)
            x = (start_coords[0] + start_coords[2]) / 2
            y = (start_coords[1] + start_coords[3]) / 2
            self.temp_line = self.canvas.create_line(x, y, event.x, event.y, arrow=tk.LAST, dash=(4, 2))
        else:
            # Check if a block is clicked for dragging
            for block in self.blocks:
                rect_coords = self.canvas.coords(block["rect"])
                if rect_coords[0] <= event.x <= rect_coords[2] and rect_coords[1] <= event.y <= rect_coords[3]:
                    self.selected_block = block
                    self.offset_x = event.x - block["x"]
                    self.offset_y = event.y - block["y"]
                    return
            # Clear the selected block if clicking elsewhere
            self.selected_block = None

    def drag_block(self, event):
        """Move the block while dragging, or update the temporary connection line."""
        if self.selected_block:
            block = self.selected_block
            dx = event.x - block["x"] - self.offset_x
            dy = event.y - block["y"] - self.offset_y
            self.canvas.move(block["rect"], dx, dy)
            self.canvas.move(block["text"], dx, dy)
            for port in block["inputs"] + block["outputs"]:
                self.canvas.move(port, dx, dy)

            # Update connection lines linked to the block
            self.update_connections(block, dx, dy)

            block["x"] += dx
            block["y"] += dy
        elif self.temp_line:
            # Update the temporary line to follow the mouse
            start_coords = self.canvas.coords(self.start_port)
            x1 = (start_coords[0] + start_coords[2]) / 2
            y1 = (start_coords[1] + start_coords[3]) / 2
            end_x, end_y = event.x, event.y
            mid_x, mid_y = x1, end_y
            self.canvas.coords(self.temp_line, x1, y1, mid_x, mid_y, end_x, end_y)

    def update_connections(self, block, dx, dy):
        """Update the positions of connections linked to a moved block."""
        for connection in self.connections:
            start_port, end_port, line = connection
            if start_port in block["outputs"] or end_port in block["inputs"]:
                start_coords = self.canvas.coords(start_port)
                end_coords = self.canvas.coords(end_port)
                self.canvas.coords(line, *self.get_orthogonal_coords(start_coords, end_coords))

    def get_orthogonal_coords(self, start_coords, end_coords):
        """Calculate orthogonal (90-degree corner) coordinates for the connection."""
        start_x = (start_coords[0] + start_coords[2]) / 2
        start_y = (start_coords[1] + start_coords[3]) / 2
        end_x = (end_coords[0] + end_coords[2]) / 2
        end_y = (end_coords[1] + end_coords[3]) / 2

        mid_x = start_x + 20 if start_x < end_x else start_x - 20
        mid_y = end_y
        return [start_x, start_y, mid_x, start_y, mid_x, mid_y, end_x, end_y]

    def complete_action(self, event):
        """Complete the current action, either connecting or moving a block."""
        if self.temp_line:
            self.canvas.delete(self.temp_line)
            self.temp_line = None

        if self.start_port:
            self.complete_connection(event)
        self.selected_block = None

    def complete_connection(self, event):
        """Complete a connection by clicking on a valid destination port."""
        if not self.start_port:
            return

        clicked_port = self.get_port_at(event.x, event.y)
        if clicked_port and self.start_port != clicked_port:
            # Check if the connection is valid
            start_type = self.get_port_type(self.start_port)
            end_type = self.get_port_type(clicked_port)

            if start_type == "output" and end_type == "input":
                # Draw a line between the ports
                start_coords = self.canvas.coords(self.start_port)
                end_coords = self.canvas.coords(clicked_port)
                line = self.canvas.create_line(
                    (start_coords[0] + start_coords[2]) / 2,
                    (start_coords[1] + start_coords[3]) / 2,
                    (end_coords[0] + end_coords[2]) / 2,
                    (end_coords[1] + end_coords[3]) / 2,
                    arrow=tk.LAST
                )
                connection = (self.start_port, clicked_port, line)
                self.connections.append(connection)
                self.history.append(("add_connection", connection))
                self.redo_stack.clear()

        # Reset the start port
        self.start_port = None

    def highlight_port(self, event):
        """Highlight ports when hovered over."""
        for block in self.blocks:
            for port in block["inputs"] + block["outputs"]:
                self.canvas.itemconfig(port, outline="")  # Reset outline

        hovered_port = self.get_port_at(event.x, event.y)
        if hovered_port:
            self.canvas.itemconfig(hovered_port, outline="yellow")

    def get_port_at(self, x, y):
        """Get the port (if any) at the given coordinates."""
        items = self.canvas.find_overlapping(x, y, x, y)
        for item in items:
            if "port" in self.canvas.gettags(item):
                return item
        return None

    def get_port_type(self, port):
        """Determine if a port is an input or output."""
        for block in self.blocks:
            if port in block["inputs"]:
                return "input"
            if port in block["outputs"]:
                return "output"
        return None

    def save_design(self):
        """Save the current design to a file."""
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            data = {
                "blocks": [
                    {
                        "x": block["x"],
                        "y": block["y"],
                        "num_inputs": block["num_inputs"],
                        "num_outputs": block["num_outputs"]
                    }
                    for block in self.blocks
                ],
                "connections": [
                    {
                        "start_port": self.canvas.coords(conn[0]),
                        "end_port": self.canvas.coords(conn[1])
                    }
                    for conn in self.connections
                ]
            }
            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)

    def load_design(self):
        """Load a design from a file."""
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, "r") as f:
                data = json.load(f)

            self.canvas.delete("all")

    def undo(self):
        """Undo the last action."""
        if not self.history:
            return

        action, data = self.history.pop()
        if action == "add_block":
            # Remove the block from canvas and memory
            self.canvas.delete(data["rect"])
            self.canvas.delete(data["text"])
            for port in data["inputs"] + data["outputs"]:
                self.canvas.delete(port)
            self.blocks.remove(data)
            self.redo_stack.append(("add_block", data))
        elif action == "add_connection":
            # Remove the connection
            self.canvas.delete(data[2])  # The line
            self.connections.remove(data)
            self.redo_stack.append(("add_connection", data))

    def redo(self):
        """Redo the last undone action."""
        if not self.redo_stack:
            return

        action, data = self.redo_stack.pop()
        if action == "add_block":
            # Recreate the block
            self.blocks.append(data)
            self.canvas.create_rectangle(*self.canvas.coords(data["rect"]), fill="lightblue")
            self.canvas.create_text(*self.canvas.coords(data["text"]))
            for port in data["inputs"] + data["outputs"]:
                self.canvas.create_oval(*self.canvas.coords(port), fill="red" if port in data["inputs"] else "green")
            self.history.append(("add_block", data))
        elif action == "add_connection":
            # Redraw the connection
            line = self.canvas.create_line(self.canvas.coords(data[0]), self.canvas.coords(data[1]), arrow=tk.LAST)
            self.connections.append((data[0], data[1], line))
            self.history.append(("add_connection", data))


if __name__ == "__main__":
    root = tk.Tk()
    app = DigitalDesignApp(root)
    root.mainloop()
