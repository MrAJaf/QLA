import streamlit as st
import pandas as pd
from fpdf import FPDF
import zipfile
import io
import os

# --- Session defaults ---
if "step" not in st.session_state:
    st.session_state.step = 1
if "all_questions" not in st.session_state:
    st.session_state.all_questions = []
if "students_df" not in st.session_state:
    st.session_state.students_df = None
if "score_inputs" not in st.session_state:
    st.session_state.score_inputs = {}
if "boundaries_df" not in st.session_state:
    st.session_state.boundaries_df = None
if "grading_scheme" not in st.session_state:
    st.session_state.grading_scheme = "GCSE (9-1)"

# --- Sidebar Reset Button ---
with st.sidebar:
    if st.button("🔄 Start Over"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.experimental_set_query_params()
        st.rerun()

# --- Step 1: Setup Assessment ---
if st.session_state.step == 1:
    st.title("🧪 Step 1: Set Up Your Assessment")
    num_papers = st.number_input("How many papers?", min_value=1, max_value=3, step=1)
    questions_per_paper = {}
    for paper in range(1, num_papers + 1):
        questions_per_paper[paper] = st.number_input(f"Questions in Paper {paper}", min_value=1, step=1, key=f"paper_{paper}")

    all_questions = []
    for paper in range(1, num_papers + 1):
        st.subheader(f"Paper {paper}")
        for q in range(1, questions_per_paper[paper] + 1):
            col1, col2 = st.columns([3, 1])
            topic = col1.text_input(f"Topic for Paper {paper}, Q{q}", key=f"topic_{paper}_{q}")
            max_marks = col2.number_input("Max Marks", min_value=1, key=f"marks_{paper}_{q}")
            if topic:
                all_questions.append({
                    "paper": paper,
                    "question_number": q,
                    "topic": topic,
                    "max_marks": max_marks
                })

    if all_questions:
        st.session_state.all_questions = all_questions
        if st.button("Next: Set Grade Boundaries"):
            st.session_state.step = 2
            st.rerun()

# --- Step 2: Grade Boundaries ---
elif st.session_state.step == 2:
    st.title("🎯 Step 2: Choose Grade Boundaries")
    scheme = st.selectbox("Grading system:", ["GCSE (9-1)", "A-Level (A*-U)"])
    st.session_state.grading_scheme = scheme

    if scheme == "GCSE (9-1)":
        grades = ["9", "8", "7", "6", "5", "4", "3", "2", "1", "U"]
        defaults = [90, 85, 75, 70, 65, 60, 50, 40, 30, 0]
    else:
        grades = ["A*", "A", "B", "C", "D", "E", "U"]
        defaults = [90, 80, 70, 60, 50, 40, 0]

    boundaries = []
    for grade, default in zip(grades, defaults):
        col1, col2 = st.columns([1, 2])
        col1.write(f"**{grade}**")
        val = col2.number_input(f"Minimum % for {grade}", min_value=0, max_value=100, value=default, key=f"gb_{grade}")
        boundaries.append({"grade": grade, "minimum_mark": val})

    st.session_state.boundaries_df = pd.DataFrame(boundaries)
    st.dataframe(st.session_state.boundaries_df)

    if st.button("Next: Upload Student List"):
        st.session_state.step = 3
        st.rerun()

# --- Step 3: Upload Students & Scores ---
elif st.session_state.step == 3:
    st.title("📥 Step 3: Upload Student List and Enter Scores")

    template = pd.DataFrame({
        "name": ["John Doe", "Jane Smith"],
        "current_grade": ["C", "B"],
        "target_grade": ["B", "A"]
    })
    st.download_button("⬇️ Download Student List Template", data=template.to_csv(index=False).encode("utf-8"), file_name="student_template.csv")

    student_file = st.file_uploader("Upload your student list CSV", type="csv")

    if student_file:
        df = pd.read_csv(student_file)
        required_cols = {"name", "current_grade", "target_grade"}
        if not required_cols.issubset(df.columns):
            st.error("Your CSV must include: name, current_grade, target_grade")
        else:
            st.session_state.students_df = df
            inputs = {}
            for idx, student in df.iterrows():
                st.subheader(f"{student['name']} | Current: {student['current_grade']} → Target: {student['target_grade']}")
                student_scores = []
                for q in st.session_state.all_questions:
                    col1, _ = st.columns([3, 1])
                    label = f"Paper {q['paper']}, Q{q['question_number']} – {q['topic']}"
                    score = col1.number_input(label, min_value=0, max_value=int(q['max_marks']), key=f"s_{idx}_{q['paper']}_{q['question_number']}")
                    student_scores.append({
                        **q,
                        "name": student["name"],
                        "current_grade": student["current_grade"],
                        "target_grade": student["target_grade"],
                        "marks_achieved": score
                    })
                inputs[student["name"]] = student_scores
            st.session_state.score_inputs = inputs
            if st.button("Next: Generate Reports"):
                st.session_state.step = 4
                st.rerun()

# --- Step 4: Generate Reports ---
elif st.session_state.step == 4:
    st.title("📄 Step 4: Generate QLA Reports")

    output_folder = "QLA_Reports"
    os.makedirs(output_folder, exist_ok=True)

    # 🔥 Clear old reports
    for file in os.listdir(output_folder):
        file_path = os.path.join(output_folder, file)
        if file.endswith(".pdf"):
            os.remove(file_path)

    boundaries = st.session_state["boundaries_df"]

    for name, scores in st.session_state["score_inputs"].items():
        pdf = FPDF()
        pdf.add_page()
        try:
            pdf.image("logo.PNG", x=165, y=8, w=30)
        except: pass

        pdf.set_font("Arial", 'B', 16)
        pdf.set_xy(10, 20)
        pdf.cell(140, 10, f"QLA Report for {name}", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, f"Current Grade: {scores[0]['current_grade']} | Target Grade: {scores[0]['target_grade']}", ln=True)

        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(80, 10, "Topic", 1, fill=True)
        pdf.cell(18, 10, "Paper", 1, fill=True)
        pdf.cell(22, 10, "Score", 1, fill=True)
        pdf.cell(22, 10, "Max", 1, fill=True)
        pdf.cell(22, 10, "%", 1, fill=True)
        pdf.cell(26, 10, "RAG", 1, fill=True)
        pdf.ln()

        total_score = 0
        total_max = 0
        for row in scores:
            percent = (row['marks_achieved'] / row['max_marks']) * 100
            rag = "Green" if percent >= 75 else "Amber" if percent >= 50 else "Red"
            fill = (144, 238, 144) if rag == "Green" else (255, 223, 100) if rag == "Amber" else (255, 160, 160)
            pdf.set_fill_color(*fill)
            pdf.cell(80, 10, row["topic"], 1, fill=True)
            pdf.cell(18, 10, str(row["paper"]), 1, fill=True)
            pdf.cell(22, 10, str(row["marks_achieved"]), 1, fill=True)
            pdf.cell(22, 10, str(row["max_marks"]), 1, fill=True)
            pdf.cell(22, 10, f"{percent:.1f}%", 1, fill=True)
            pdf.cell(26, 10, rag, 1, fill=True)
            pdf.ln()
            total_score += row['marks_achieved']
            total_max += row['max_marks']

        overall = (total_score / total_max) * 100
        pdf.set_fill_color(220, 220, 220)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(98, 10, "TOTAL", 1, fill=True)
        pdf.cell(22, 10, str(total_score), 1, fill=True)
        pdf.cell(22, 10, str(total_max), 1, fill=True)
        pdf.cell(22, 10, f"{overall:.1f}%", 1, fill=True)
        pdf.cell(26, 10, "", 1, fill=True)
        pdf.ln()

        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Grade Boundaries", ln=True)
        pdf.set_font("Arial", size=12)
        for _, row in boundaries.iterrows():
            pdf.cell(40, 8, f"{row['grade']}:", border=0)
            pdf.cell(40, 8, f"{row['minimum_mark']}%", border=0)
            pdf.ln()

        pdf.ln(10)
        pdf.cell(0, 10, "What did I do well?", ln=True)
        pdf.rect(x=10, y=pdf.get_y(), w=190, h=25)
        pdf.ln(30)
        pdf.cell(0, 10, "Which topics do I need to revisit?", ln=True)
        pdf.rect(x=10, y=pdf.get_y(), w=190, h=25)
        pdf.ln(30)
        pdf.cell(0, 10, "What actions will I take before the next test?", ln=True)
        pdf.rect(x=10, y=pdf.get_y(), w=190, h=25)

        filename = name.replace(" ", "_") + "_QLA_Report.pdf"
        pdf.output(os.path.join(output_folder, filename))

    # Create ZIP
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zipf:
        for fname in os.listdir(output_folder):
            if fname.endswith(".pdf"):
                zipf.write(os.path.join(output_folder, fname), arcname=fname)
    zip_buf.seek(0)

    st.success("✅ Reports ready!")
    st.download_button("⬇️ Download All Reports as ZIP", data=zip_buf, file_name="QLA_Reports.zip", mime="application/zip")
