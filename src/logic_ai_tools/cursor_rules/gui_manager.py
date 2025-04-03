import tkinter as tk
from tkinter import ttk
import os
import glob
from cc_ai_tools.cursor_rules.file_operations import get_rules_dir
from cc_ai_tools.cursor_rules.project_scanner import ProjectScanner

def select_files(grouped_files, project_folder):
    if not grouped_files:
        print("No rules files found!")
        return []
    
    root = tk.Tk()
    root.title("Select Rules Files")
    root.geometry("1200x800")
    
    # Store selected files and project rule state
    selected_files_list = []
    include_project_rule = tk.BooleanVar(value=False)
    project_rule_text = None
    
    # Create main container with left and right panels
    main_container = ttk.Frame(root, padding="10")
    main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    # Left panel for project rule
    left_panel = ttk.Frame(main_container, padding="5", relief="solid")
    left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
    
    # Project rule header
    ttk.Label(left_panel, text="Project Rule", font=('TkDefaultFont', 12, 'bold')).grid(row=0, column=0, sticky="w", pady=(0, 5))
    
    # Project rule text area
    project_rule_text = tk.Text(left_panel, wrap=tk.WORD, width=50, height=30)
    project_rule_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
    
    # Load existing project context file if it exists
    context_file = os.path.join(get_rules_dir(project_folder), "project-context.mdc")
    if os.path.exists(context_file):
        with open(context_file, 'r', encoding='utf-8') as f:
            project_rule_text.delete(1.0, tk.END)
            project_rule_text.insert(tk.END, f.read())
            include_project_rule.set(True)  # Auto-check the include box
    
    # Scrollbar for project rule text
    project_rule_scroll = ttk.Scrollbar(left_panel, orient="vertical", command=project_rule_text.yview)
    project_rule_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S))
    project_rule_text.configure(yscrollcommand=project_rule_scroll.set)
    
    # Scan project button
    def scan_project():
        scanner = ProjectScanner(project_folder)
        content = scanner.scan_project()  # Now returns content instead of writing file
        if content:
            project_rule_text.delete(1.0, tk.END)
            project_rule_text.insert(tk.END, content)
            include_project_rule.set(True)  # Auto-check the include box
    
    ttk.Button(left_panel, text="Scan Project", command=scan_project).grid(row=2, column=0, sticky="ew", pady=(0, 5))
    
    # Include project rule checkbox
    ttk.Checkbutton(
        left_panel,
        text="Include project rule in selection",
        variable=include_project_rule
    ).grid(row=3, column=0, sticky="w")
    
    # Right panel for rule selection
    right_panel = ttk.Frame(main_container)
    right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    # Add search frame at the top of right panel
    search_frame = ttk.Frame(right_panel)
    search_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
    ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
    search_var = tk.StringVar()
    search_entry = ttk.Entry(search_frame, textvariable=search_var)
    search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # Create canvas with scrollbar for rule selection
    canvas = tk.Canvas(right_panel)
    scrollbar = ttk.Scrollbar(right_panel, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Variables to store checkbox states and widgets
    checkboxes = {}
    checkbox_widgets = {}
    group_widgets = {}
    
    def check_group(group):
        state = group_vars[group].get()
        for checkbox in group_checkboxes[group]:
            checkbox.set(state)
    
    group_vars = {}
    group_checkboxes = {}
    
    # Create all widgets
    row = 0
    # Sort groups to ensure consistent order
    sorted_groups = sorted(grouped_files.keys())
    for group in sorted_groups:
        # Group header and checkbox
        group_frame = ttk.Frame(scrollable_frame)
        group_frame.grid(row=row, column=0, sticky="w", pady=(10,5))
        group_widgets[group] = group_frame
        
        group_vars[group] = tk.BooleanVar()
        group_checkboxes[group] = []
        
        ttk.Checkbutton(
            group_frame,
            text=group,
            variable=group_vars[group],
            command=lambda g=group: check_group(g)
        ).pack(side=tk.LEFT)
        
        row += 1
        
        # File checkboxes
        for file_info in grouped_files[group]:
            var = tk.BooleanVar()
            checkboxes[file_info['path']] = var
            group_checkboxes[group].append(var)
            
            exists = file_info['exists']
            
            # Create checkbox
            checkbox = ttk.Checkbutton(
                scrollable_frame,
                text=file_info['path'],
                variable=var,
                padding=(20, 0, 0, 0)
            )
            
            checkbox.grid(row=row, column=0, sticky="w")
            checkbox_widgets[file_info['path']] = checkbox
            
            # If rule exists, check it by default
            if exists:
                var.set(True)
            
            row += 1
    
    def filter_rules(*args):
        search_text = search_var.get().lower()
        
        # Reset visibility of all widgets
        for group in group_widgets:
            group_widgets[group].grid_remove()
            
        for file in checkbox_widgets:
            checkbox_widgets[file].grid_remove()
            
        # Show only matching items
        row = 0
        for group, files in grouped_files.items():
            group_visible = False
            if search_text in group.lower():
                group_visible = True
            
            matching_files = [f for f in files if search_text in f['path'].lower()]
            if matching_files:
                group_visible = True
            
            if group_visible:
                group_widgets[group].grid(row=row, column=0, sticky="w", pady=(10,5))
                row += 1
                
                for file_info in files:
                    if search_text in file_info['path'].lower():
                        checkbox_widgets[file_info['path']].grid(row=row, column=0, sticky="w")
                        row += 1
    
    # Bind search box to filter function
    search_var.trace("w", filter_rules)
    
    def confirm_selection():
        nonlocal selected_files_list
        selected_files_list = [file_info['path'] for file_info in grouped_files.values() for file_info in file_info if checkboxes[file_info['path']].get()]
        
        # If project rule is enabled and contains text, save it
        if include_project_rule.get() and project_rule_text and project_rule_text.get(1.0, tk.END).strip():
            project_rule_path = os.path.join(get_rules_dir(project_folder), "project-context.mdc")
            with open(project_rule_path, 'w', encoding='utf-8') as f:
                f.write(project_rule_text.get(1.0, tk.END))
            if "project-context.mdc" not in selected_files_list:
                selected_files_list.append("project-context.mdc")
        
        root.quit()
    
    ttk.Button(
        main_container,
        text="Apply Rules",  # Changed text to be more clear
        command=confirm_selection
    ).grid(row=1, column=0, columnspan=2, pady=10)
    
    # Grid layout for scrollbar and configure grid weights
    canvas.grid(row=1, column=0, sticky="nsew")
    scrollbar.grid(row=1, column=1, sticky="ns")
    
    # Configure grid weights for expansion
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    main_container.grid_rowconfigure(0, weight=1)
    main_container.grid_columnconfigure(1, weight=3)  # Right panel gets more space
    right_panel.grid_rowconfigure(1, weight=1)
    right_panel.grid_columnconfigure(0, weight=1)
    left_panel.grid_rowconfigure(1, weight=1)
    left_panel.grid_columnconfigure(0, weight=1)
    
    # Set minimum size for the window
    root.minsize(800, 600)
    
    root.mainloop()
    
    try:
        root.destroy()
    except:
        pass
        
    return selected_files_list 