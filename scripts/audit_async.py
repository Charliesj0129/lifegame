import ast
import os
import sys

KNOWN_SYNC_METHODS = {
    "add_node",
    "query",
    "record_user_event",
    "get_user_history",
    "add_quest_dependency",
    "get_unlockable_templates",
    # add_relationship is async in adapter.py wrapper, so safe to await
}

KNOWN_ADAPTER_NAMES = {"adapter", "kuzu_adapter"}

class AsyncAwaitVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.issues = []

    def visit_Await(self, node):
        # We are looking for await <call>
        if isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute):
                method_name = call.func.attr
                
                # Check if method is known sync
                if method_name in KNOWN_SYNC_METHODS:
                    # Check if caller looks like an adapter
                    caller = call.func.value
                    caller_name = ""
                    if isinstance(caller, ast.Name):
                        caller_name = caller.id
                    elif isinstance(caller, ast.Attribute):
                        caller_name = caller.attr
                    
                    if caller_name in KNOWN_ADAPTER_NAMES:
                        # Check if it's NOT wrapped in asyncio.to_thread
                        # Actually strict await adapter.method() is the bug.
                        # await asyncio.to_thread(adapter.method) is AST: Await(Call(func=Attribute(value=Name(asyncio), attr=to_thread), args=[Attribute(adapter, method)]))
                        # The node.value we are visiting is the Call to to_thread.
                        # So if we are visiting Await(Call(func=Attribute(..., attr='add_node'))), it is the bug.
                         self.issues.append(
                            f"{self.filename}:{node.lineno} - await {caller_name}.{method_name}(...) detected. "
                            f"{method_name} is synchronous in KuzuAdapter!"
                        )

        self.generic_visit(node)

def audit_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)
        visitor = AsyncAwaitVisitor(filepath)
        visitor.visit(tree)
        return visitor.issues
    except Exception as e:
        return [f"Could not parse {filepath}: {e}"]

def main():
    root_dir = os.getcwd()
    all_issues = []
    
    print("🔍 Starting Async/Sync Mismatch Audit...")
    
    ignore_dirs = {".venv", "__pycache__", ".git", "legacy"}
    
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                issues = audit_file(path)
                all_issues.extend(issues)

    if all_issues:
        print(f"❌ Found {len(all_issues)} issues:")
        for issue in all_issues:
            print(issue)
        sys.exit(1)
    else:
        print("✅ No usage of await on known synchronous KuzuAdapter methods found.")
        sys.exit(0)

if __name__ == "__main__":
    main()
