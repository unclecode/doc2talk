import os
import doc2talk
from doc2talk import Doc2Talk

__curr_dir = os.path.dirname(os.path.abspath(__file__))
__parent_dir = os.path.dirname(__curr_dir)
print(f"Current directory: {__curr_dir}")
print(f"Parent directory: {__parent_dir}")
# Check if the current directory is the root of the project
if os.path.exists(f"{__curr_dir}/src") and os.path.exists(f"{__curr_dir}/docs"):
    __parent_dir = __curr_dir

code_source = f"{__parent_dir}/src" if os.path.exists(f"{__parent_dir}/src") else None
docs_source = f"{__parent_dir}/docs" if os.path.exists(f"{__parent_dir}/docs") else None

# Print version
print(f"doc2talk version: {doc2talk.__version__}")

doc = Doc2Talk(code_source=code_source, docs_source=docs_source)
print(f"Successfully created Doc2Talk instance with session ID: {doc.session_id}")

print("Building index before chatting...")
doc.build_index()  # This builds the index without sending any messages
print("Index built successfully")

question = "How does the Doc2Talk work?"
print(f"Question: {question}")
response = doc.chat(question)
print(f"Response:\n{response}")


assert response is not None, "Response should not be None"

print("Import test successful!")