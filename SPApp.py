# Importing necessary libraries
import streamlit as st
import io
import hashlib
import requests
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
from reportlab.lib.pagesizes import letter, landscape, portrait
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from io import BytesIO
import base64
from PIL import UnidentifiedImageError
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from PIL import Image, ImageOps
from reportlab.platypus import Image as PlatypusImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak






# Setting up connection to the database
conn = sqlite3.connect('proposal.db')
c = conn.cursor()

# Creating Users table in the database
c.execute('''CREATE TABLE IF NOT EXISTS Users (username TEXT PRIMARY KEY, password TEXT)''')

# Creating Proposals table in the database
c.execute('''CREATE TABLE IF NOT EXISTS Proposals (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, data TEXT)''')


# Define a function to hash a password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Define a function to verify a password
def verify_password(password, hash):
    return hash_password(password) == hash


def dashboard(username):
    st.sidebar.header('Options')
    st.sidebar.write('Please select an option from the sidebar.')
    option = st.sidebar.selectbox('Select an option', ['Proposal Generator', 'Saved Proposals'])
    if option == 'Proposal Generator':
        proposal_generator(username)
    elif option == 'Saved Proposals':
        display_saved_proposals(username)
        pass




# Streamlit app begins here
def main():
    st.set_page_config(page_title='Solar PV Proposal Generator')
    st.title('Solar PV Proposal Generator')

    menu = ['Home', 'Login', 'SignUp']
    choice = st.sidebar.selectbox('Select an option', menu)

    # Home Page
    if choice == 'Home':
        st.subheader('Welcome to Solar PV Proposal Generator!')
        st.write('Please login or signup to generate proposals.')

    # Login Page
    elif choice == 'Login':
        st.subheader('Login')
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        if st.button('Login'):
            if username and password:
                c.execute("SELECT * FROM Users WHERE username=?", (username,))
                user = c.fetchone()
                if user:
                    if verify_password(password, user[1]):
                        st.success('Logged in successfully!')
                        session_id = username
                        st.session_state[session_id] = True
                        st.experimental_set_query_params(logged_in=True, username=session_id)
                        dashboard(username)
                    else:
                        st.error('Incorrect username/password')
                else:
                    st.error('User does not exist')
            else:
                st.warning('Please enter username/password')

    # SignUp Page
    elif choice == 'SignUp':
        st.subheader('SignUp')
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        confirm_password = st.text_input('Confirm Password', type='password')
        if st.button('SignUp'):
            if username and password and confirm_password:
                if password == confirm_password:
                    hashed_password = hash_password(password)
                    try:
                        c.execute("INSERT INTO Users (username, password) VALUES (?,?)", (username, hashed_password))
                        conn.commit()
                        st.success('Account created successfully!')
                        st.info('Please login to continue.')
                    except:
                        st.error('Username already exists')
                else:
                    st.error('Passwords do not match')
            else:
                st.warning('Please enter username/password')

    # Dashboard Page
    elif 'logged_in' in st.experimental_get_query_params():
        logged_in = st.experimental_get_query_params()['logged_in']
        username = st.experimental_get_query_params()['username']
        if logged_in and st.session_state.get(username):
            st.subheader(f'Welcome, {username}!')
            st.write('Please select an option from the sidebar.')
            option = st.sidebar.selectbox('Select an option', ['Proposal Generator', 'Saved Proposals'])
            if option == 'Proposal Generator':
                proposal_generator(username)
            elif option == 'Saved Proposals':
                display_saved_proposals(username)
                # Add code for displaying saved proposals in the dashboard
                pass
        else:
            st.error('Please login to continue.')
            st.stop()

    # Invalid Page
    else:
        st.error('Invalid Page')




def generate_pdf(company_name, num_employees, key_employees, projects, mission, vision, map_image, project_details, commercial_details, payment_terms):
    # Define styles for the PDF proposal
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='centered', alignment=TA_CENTER))

    # Define the elements for the PDF proposal
    elements = []

    # Add the company details to the first page
    elements.append(Paragraph(f'<b>{company_name}</b>', styles['Title']))
    elements.append(Spacer(1, 0.25 * inch))
    elements.append(Paragraph(f'Total number of employees: {num_employees}', styles['Normal']))
    elements.append(Paragraph(f'Key management employees: {key_employees}', styles['Normal']))
    elements.append(Spacer(1, 0.25 * inch))
    elements.append(Paragraph('<b>Top 3 Projects:</b>', styles['Normal']))
    for project in projects:
        project_details = f'<b>{project["name"]}:</b> {project["description"]}'
        elements.append(Paragraph(project_details, styles['Normal']))
        elements.append(PlatypusImage(requests.get(project['thumbnail']).content, width=2*inch, height=2*inch))
    elements.append(Spacer(1, 0.25 * inch))
    elements.append(Paragraph(f'<b>Mission:</b> {mission}', styles['Normal']))
    elements.append(Paragraph(f'<b>Vision:</b> {vision}', styles['Normal']))
    elements.append(PageBreak())

    # Add the project details to the second page
    elements.append(Paragraph('<b>Google Map Image (6:4 Ratio)</b>', styles['Normal']))
    map_img = Image.open(io.BytesIO(requests.get(map_image).content))
    map_img_width, map_img_height = map_img.size
    map_img_ratio = map_img_width / map_img_height
    if map_img_ratio > 1.5:
        # Crop the image horizontally to fit the 6:4 ratio
        left = (map_img_width - map_img_height * 1.5) / 2
        right = map_img_width - left
        map_img = map_img.crop((left, 0, right, map_img_height))
    else:
        # Pad the image horizontally to fit the 6:4 ratio
        pad_width = int((map_img_height * 1.5 - map_img_width) / 2)
        map_img = ImageOps.expand(map_img, border=(pad_width, 0, pad_width, 0), fill='white')
    elements.append(Image(map_img, width=6*inch, height=4*inch))
    elements.append(Paragraph(f'<b>Project Details:</b>', styles['Normal']))
    project_table = Table(project_details, colWidths=[2.5*inch, 3*inch])
    project_table.setStyle(TableStyle([('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                        ('ALIGN', (0, 0),(-1, -1), 'Helvetica'),
                                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                    ('GRID', (0, 0), (-1, -1), 0.5, 'black')]))
    elements.append(project_table)
    elements.append(Spacer(1, 0.25 * inch))
    elements.append(Paragraph(f'<b>Commercial Details:</b>', styles['Normal']))
    commercial_table = Table(commercial_details, colWidths=[2.5*inch, 3*inch])
    commercial_table.setStyle(TableStyle([('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                            ('GRID', (0, 0), (-1, -1), 0.5, 'black')]))
    elements.append(commercial_table)
    elements.append(Spacer(1, 0.25 * inch))
    elements.append(Paragraph(f'<b>Payment Terms:</b>', styles['Normal']))
    elements.append(Paragraph(payment_terms, styles['Normal']))

    # Generate the PDF proposal
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=portrait(letter), rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf








# proposal_generator function

def proposal_generator(username):
    #st.subheader('Solar PV Proposal Generator')
    #session_id = st.session_state.get('username')
   # if not session_id:
       # st.error('Please login to generate proposals.')
      #  st.stop()

    st.write('Please fill in the details below:')
    company_name = st.text_input('Company Name')
    num_employees = st.number_input('Number of Employees')
    key_employees = st.text_area('Key Management Employees')
    projects = st.text_area('Top 3 Projects (Briefs)')
    mission = st.text_area('Company Mission')
    vision = st.text_area('Company Vision')
    
    st.subheader('Project Details')
    project_capacity = st.number_input('Project Capacity (kW)')
    num_panels = st.number_input('Number of Solar Panels')
    panel_brand = st.text_input('Solar Panel Brand')
    panel_model = st.text_input('Solar Panel Model')
    num_dc_strings = st.number_input('Total Number of DC Strings')
    num_inverters = st.number_input('Number of Solar Inverters')
    inverter_brand = st.text_input('Inverter Brand')
    inverter_model = st.text_input('Inverter Model')
    inverter_type = st.text_input('Inverter Type')
    system_voltage = st.number_input('System Voltage in V')
    poc_voltage = st.number_input('Point of Connection Voltage')
    num_ac_combiners = st.number_input('Number of AC Combiner Boxes')
    transformer_details = st.text_input('Transformer Details (if required)')

    st.subheader('Commercial and Financial Details')
    energy_yield = st.number_input('Total Expected Energy Yield for the First Year (kWh)')
    pr_ratio = st.number_input('First Year Plant Performance Ratio (PR)')
    project_cost = st.number_input('Total Project Cost Offered to Client ($)')
    tariff = st.number_input('Current Electricity Tariff ($/kWh)')
    savings = st.number_input('Electricity Savings per Year ($)')
    om_cost = st.number_input('Yearly O&M Cost ($)')
    project_details = [['Scope of Work:', st.text_input('Scope of Work')],
                       ['Deliverables:', st.text_input('Deliverables')],
                       ['Timeline:', st.text_input('Timeline')],
                       ['Pricing:', st.text_input('Pricing')]]
    commercial_details = [['Commercial Terms:', st.text_input('Commercial Terms')],
                          ['Tax:', st.number_input('Tax', min_value=0.0, step=0.01)],
                          ['Discount:', st.number_input('Discount', min_value=0.0, step=0.01)],
                          ['Total Price:', 0]]

    st.subheader('Google Map')
    address = st.text_input('Project Address')
    api_key = 'AIzaSyAMywKJAPs-rkIFRqx0--5PFBa_qcMpXcQ'
    url = f'https://maps.googleapis.com/maps/api/staticmap?center={address}&size=800x533&zoom=13&maptype=roadmap&markers=color:red%7C{address}&key={api_key}'
    response = requests.get(url)
    map_image = BytesIO(response.content)
    try:
        st.image(map_image, caption='Google Map Image (6:4 Ratio)')
    except UnidentifiedImageError:
        st.error('Unable to display image: invalid or unsupported format.')
    

    st.subheader('Terms & Conditions')
    payment_terms = st.text_area('Payment Terms')
    project_schedule = st.text_area('Project Schedule')
    
    if st.button('Generate Proposal'):
        # Creating the PDF proposal
        
        filename = f"{company_name.replace(' ', '_')}_proposal.pdf"
        doc = canvas.Canvas(filename, pagesize=landscape(letter))

        # Adding the first page
        doc.setFont('Helvetica-Bold', 18)
        doc.drawString(1*inch, 10*inch, company_name)
        doc.setFont('Helvetica', 12)
        doc.drawString(1*inch, 9.5*inch, f"Number of Employees: {num_employees}")
        doc.drawString(1*inch, 9.2*inch, f"Key Management Employees: {key_employees}")
        doc.drawString(1*inch, 8.9*inch, "Top 3 Projects (Briefs):")
        for i, project in enumerate(projects.split('\n')):
            doc.drawString(1.1*inch, (8.7-i*0.3)*inch, f"{i+1}. {project}")
        doc.drawString(1*inch, 8*inch, f"Company Mission: {mission}")
        doc.drawString(1*inch, 8*inch, f"Company Vision: {vision}")
        #doc.drawImage(map_image, 1*inch, 4.5*inch, width=5*inch, height=3.3*inch)
        doc.drawString(1*inch, 4*inch, f"Project Address: {address}")

        # Adding the second page
        doc.showPage()
        doc.setFont('Helvetica-Bold', 18)
        doc.drawString(1*inch, 10*inch, 'Project Details')
        doc.setFont('Helvetica', 12)
        doc.drawString(1*inch, 9.5*inch, f"Project Capacity (kW): {project_capacity}")
        doc.drawString(1*inch, 9.2*inch, f"Number of Solar Panels: {num_panels}")
        doc.drawString(1*inch, 8.9*inch, f"Solar Panel Brand: {panel_brand}")
        doc.drawString(1*inch, 8.6*inch, f"Solar Panel Model: {panel_model}")
        doc.drawString(1*inch, 8.3*inch, f"Total Number of DC Strings: {num_dc_strings}")
        doc.drawString(1*inch, 8*inch, f"Number of Solar Inverters: {num_inverters}")
        doc.drawString(1*inch, 7.7*inch, f"Inverter Brand: {inverter_brand}")
        doc.drawString(1*inch, 7.4*inch, f"Inverter Model: {inverter_model}")
        doc.drawString(1*inch, 7.1*inch, f"Inverter Type: {inverter_type}")
        doc.drawString(1*inch, 6.8*inch, f"Total System Voltage: {system_voltage}")
        doc.drawString(1*inch, 6.5*inch, f"Point of Connection Voltage: {poc_voltage}")
        doc.drawString(1*inch, 6.2*inch, f"Number of AC Combiner Boxes: {num_ac_combiners}")
        doc.drawString(1*inch, 5.9*inch, f"Transformer Details (if required): {transformer_details}")
        
        # Adding the third page
        doc.showPage()
        doc.setFont('Helvetica-Bold', 18)
        doc.drawString(1*inch, 10*inch, 'Commercial and Financial Details')
        doc.setFont('Helvetica', 12)
        doc.drawString(1*inch, 9.5*inch, f"Total Expected Energy Yield for the First Year (kWh): {energy_yield}")
        doc.drawString(1*inch, 9.2*inch, f"First Year Plant Performance Ratio (PR): {pr_ratio}")
        doc.drawString(1*inch, 8.9*inch, f"Total Project Cost Offered to Client ($): {project_cost}")
        doc.drawString(1*inch, 8.6*inch, f"Current Electricity Tariff ($/kWh): {tariff}")
        doc.drawString(1*inch, 8.3*inch, f"Electricity Savings per Year ($): {savings}")
        doc.drawString(1*inch, 8*inch, f"Yearly O&M Cost ($): {om_cost}")
        
        # Adding the fourth page
        doc.showPage()
        doc.setFont('Helvetica-Bold', 18)
        doc.drawString(1*inch, 10*inch, 'Terms & Conditions')
        doc.setFont('Helvetica', 12)
        doc.drawString(1*inch, 9.5*inch, f"Payment Terms: {payment_terms}")
        doc.drawString(1*inch, 9.2*inch, f"Project Schedule: {project_schedule}")
        
        
        doc.save()



    # Generate a unique filename for the proposal
        filename = f"{company_name} Solar PV Proposal.pdf"
        
        # Generate the PDF proposal
        pdf = generate_pdf(company_name, num_employees, key_employees, projects, mission, vision, project_details, commercial_details, payment_terms)
        
        # Save the PDF proposal to disk
        with open(filename, "wb") as f:
            f.write(pdf)
        
        # Download the PDF proposal
        with open(filename, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            href = f'<a href="data:application/octet-stream;base64,{base64_pdf}" download="{filename}">Download Proposal</a>'
            st.markdown(href, unsafe_allow_html=True)


def display_saved_proposals(username):
    c.execute("SELECT * FROM Proposals WHERE username=?", (username,))
    proposals = c.fetchall()
    if proposals:
        for proposal in proposals:
            st.write(f"Proposal Name: {proposal[1]}")
            st.write(f"Company Name: {proposal[2]}")
            # Add other proposal details here
            st.write('---')
    else:
        st.write('No saved proposals found.')




if __name__ == '__main__':
    main()
