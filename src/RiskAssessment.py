
import gradio as gr
from gradio import themes
import os
from dotenv import find_dotenv, load_dotenv
import requests
import base64
from pathlib import Path
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Load environment variables from .env file
load_dotenv(find_dotenv())

class FeatureState:
    def __init__(self):
        self.srs_content = None
        self.project_summary = None
        self.feature_details = None
        self.approved_features = None  # New field to store approved features

# Create a global state object
state = FeatureState()

def generate_summary_and_extract_features(pdf_path):
    """Generate summary and extract features from PDF file using the API"""
    try:
        base_url = "https://risk-assessment-app.onrender.com"
        
        # Read the PDF file and encode it as base64
        with open(pdf_path, 'rb') as file:
            pdf_content = base64.b64encode(file.read()).decode('utf-8')

        # First, generate summary
        summary_endpoint = f"{base_url}/summary/generate"
        summary_payload = {
            "content": pdf_content,
            "project_name": Path(pdf_path).stem
        }
        
        summary_response = requests.post(
            summary_endpoint, 
            headers={'Content-Type': 'application/json'},
            json=summary_payload
        )
        summary_response.raise_for_status()
        summary_result = summary_response.json()
        
        # Store the SRS content and project summary
        state.srs_content = summary_result.get("srs_text", "")
        state.project_summary = summary_result.get("project_summary", "")
        
        # Then, extract features using the summary
        features_endpoint = f"{base_url}/features/extract"
        features_payload = {
            "srs_content": state.srs_content,
            "project_summary": state.project_summary
        }
        
        features_response = requests.post(
            features_endpoint,
            headers={'Content-Type': 'application/json'},
            json=features_payload
        )
        features_response.raise_for_status()
        
        state.feature_details = features_response.json().get("feature_details", "No features extracted")
        return state.feature_details

    except requests.exceptions.RequestException as e:
        print(f"API Error: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Response text: {e.response.text}")
        return f"API Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

def re_evaluate_features(previous_features, feedback):
    """Re-evaluate features based on feedback"""
    try:
        base_url = "https://risk-assessment-app.onrender.com"
        endpoint = f"{base_url}/features/re-evaluate"
        
        payload = {
            "srs_content": state.srs_content,
            "project_summary": state.project_summary,
            "previous_features": previous_features,
            "user_feedback": feedback
        }
        
        response = requests.post(
            endpoint,
            headers={'Content-Type': 'application/json'},
            json=payload
        )
        response.raise_for_status()
        
        state.feature_details = response.json().get("feature_details", "No features re-evaluated")
        return state.feature_details
    except Exception as e:
        return f"Error in re-evaluation: {str(e)}"

async def process_documents_with_status(uploaded_file):
    """Process documents with status updates while waiting for API response"""
    if not uploaded_file:
        yield (
            "Please upload a requirements document first.",  # features output
            gr.update(visible=False),  # feedback section
            gr.update(visible=False),  # risk section
            ""  # status message
        )
        return  # Exit the generator

    # Start API call in a separate thread
    with ThreadPoolExecutor() as executor:
        future = executor.submit(generate_summary_and_extract_features, uploaded_file.name)
        
        # Show status messages while waiting for API response
        messages = [
            "Processing document...",
            "Creating Knowledge graph...",
            "Retrieving Nodes and Edges...",
            "Thinking...",
            "Generating Response..."
        ]
        
        for message in messages:
            if future.done():
                break
            yield (
                "",  # features output (empty while processing)
                gr.update(visible=False),  # feedback section
                gr.update(visible=False),  # risk section
                message  # status message
            )
            await asyncio.sleep(10)
        
        # Get API response
        features = future.result()
        
        # Yield final results
        yield (
            features,
            gr.update(visible=True),
            gr.update(visible=True),
            "Response Generated!"
        )

async def handle_feedback_with_status(feedback, features):
    """Handle feedback submission with status updates"""
    if not feedback.strip():
        yield (
            "Please provide feedback before submitting.",  # features output
            gr.update(visible=True),  # feedback section
            gr.update(visible=True),  # risk section
            "Feedback cannot be empty"  # status message
        )
        return

    # Start API call in a separate thread
    with ThreadPoolExecutor() as executor:
        future = executor.submit(re_evaluate_features, features, feedback)
        
        # Show status messages while waiting for API response
        messages = [
            "Processing feedback...",
            "Analyzing feedback content...",
            "Updating feature extraction...",
            "Generating revised features..."
        ]
        
        for message in messages:
            if future.done():
                break
            yield (
                "",  # features output (empty while processing)
                gr.update(visible=True),  # feedback section
                gr.update(visible=True),  # risk section
                message  # status message
            )
            await asyncio.sleep(5)  # Shorter interval for feedback processing
        
        # Get API response
        new_features = future.result()
        
        # Yield final results
        yield (
            new_features,
            gr.update(visible=True),
            gr.update(visible=True),
            "Feedback processed successfully!"
        )

def approve_features(features):
    """Handle feature approval and store the features"""
    state.approved_features = features
    return "Features have been approved!", gr.update(visible=False), gr.update(visible=True)

async def analyze_risks_with_status(features):
    """Analyze risks with status updates while waiting for API response"""
    try:
        if not state.approved_features:
            yield (
                "Please approve features first before analyzing risks.",
                "No approved features found"
            )
            return

        base_url = "https://risk-assessment-app.onrender.com"
        endpoint = f"{base_url}/api/risks/analyze"
        
        payload = {
            "features": state.approved_features,
            "srs_content": state.srs_content,
            "project_summary": state.project_summary
        }

        # Show initial status
        yield (
            "",
            "Initiating risk analysis..."
        )

        with ThreadPoolExecutor() as executor:
            future = executor.submit(
                lambda: requests.post(
                    endpoint,
                    headers={'Content-Type': 'application/json'},
                    json=payload
                )
            )

            # Status messages while waiting
            messages = [
                "Analyzing security risks...",
                "Identifying vulnerabilities...",
                "Evaluating compliance requirements...",
                "Generating mitigation strategies...",
                "Preparing final report..."
            ]

            for message in messages:
                if future.done():
                    break
                yield (
                    "",  # risk analysis output (empty while processing)
                    message  # status message
                )
                await asyncio.sleep(5)

            # Get API response
            response = future.result()
            response.raise_for_status()
            
            risk_analysis = response.json().get("risk_analysis", "No risks identified")
            
            # Yield final results
            yield (
                risk_analysis,  # risk analysis output
                "Risk analysis completed successfully!"  # status message
            )

    except requests.exceptions.RequestException as e:
        error_message = f"API Error: {str(e)}"
        if hasattr(e.response, 'text'):
            error_message += f"\nResponse: {e.response.text}"
        yield (
            error_message,
            "Error occurred during risk analysis"
        )
    except Exception as e:
        yield (
            f"Error: {str(e)}",
            "Error occurred during risk analysis"
        )

# Gradio UI
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        ## Security Risk Assessment Using Multi-Agent RAG
        Upload your requirements specification document and the system will analyze potential security risks,
        vulnerabilities, and provide recommendations for security improvements.
        """
    )
    
    # Upload section
    with gr.Column():
        uploaded_file = gr.File(
            file_count="single", 
            file_types=[".pdf"], 
            label="Upload Requirements Specification Document"
        )
        
        extract_features_btn = gr.Button("Extract Features", variant="primary")
        
        # Status message box (shared between document processing and feedback)
        status_box = gr.Textbox(
            label="Status",
            value="",
            interactive=False
        )
        
        # Features output section
        features_output = gr.Markdown(
            label="Extracted Features",
            value=""
        )

        # Feedback section (initially hidden)
        with gr.Column(visible=False) as feedback_section:
            feedback_input = gr.Textbox(
                label="Provide Feedback",
                lines=3,
                placeholder="Enter your feedback here if you want the features to be re-evaluated..."
            )
            
            with gr.Row():
                submit_feedback_btn = gr.Button("Submit Feedback", variant="secondary")
                approve_features_btn = gr.Button("Approve Features", variant="primary")

        # Risk Analysis section (initially hidden)
        with gr.Column(visible=False) as risk_section:
            analyze_risks_btn = gr.Button("Analyze Risks", variant="primary")
            risk_analysis_output = gr.Markdown(
                label="Risk Analysis Report",
                value=""
            )

    # Event handlers
    extract_features_btn.click(
        fn=process_documents_with_status,
        inputs=[uploaded_file],
        outputs=[
            features_output,
            feedback_section,
            risk_section,
            status_box
        ]
    )
    
    submit_feedback_btn.click(
        fn=handle_feedback_with_status,
        inputs=[feedback_input, features_output],
        outputs=[
            features_output,
            feedback_section,
            risk_section,
            status_box
        ]
    )
    
    approve_features_btn.click(
        approve_features,
        inputs=[features_output],
        outputs=[status_box, feedback_section, risk_section]
    )

    analyze_risks_btn.click(
        fn=analyze_risks_with_status,
        inputs=[features_output],
        outputs=[
            risk_analysis_output,
            status_box
        ],
        api_name="analyze_risks"
    )

if __name__ == "__main__":
    demo.launch()
