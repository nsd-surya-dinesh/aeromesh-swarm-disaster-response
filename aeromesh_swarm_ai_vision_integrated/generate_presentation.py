import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)  # 16:9 widescreen layout
    blank_layout = prs.slide_layouts[6]

    # Color Palette - Modern Aerospace Dark/Navy Theme
    C_BG_DARK = RGBColor(11, 25, 44)       # #0B192C (Deep Navy)
    C_BG_LIGHT = RGBColor(245, 247, 250)   # #F5F7FA (Off White)
    C_CARD_BG = RGBColor(255, 255, 255)    # Pure White
    C_CARD_DARK = RGBColor(20, 38, 64)     # #142640 (Card on Dark)
    C_PRIMARY = RGBColor(30, 62, 98)       # #1E3E62 (Slate Blue)
    C_ACCENT = RGBColor(255, 101, 0)       # #FF6500 (Vibrant Orange / Aerotech)
    C_ACCENT_BLUE = RGBColor(0, 168, 232)  # #00A8E8 (Cyan Blue)
    C_TEXT_DARK = RGBColor(33, 37, 41)     # #212529 (Dark Gray)
    C_TEXT_LIGHT = RGBColor(240, 244, 248) # #F0F4F8 (Light Gray)
    C_TEXT_MUTED = RGBColor(108, 117, 125) # #6C757D
    C_GREEN = RGBColor(40, 167, 69)        # Success green
    C_BORDER = RGBColor(220, 226, 235)

    def set_slide_bg(slide, color):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background() # No border
        return bg

    def add_header(slide, title_text, category_text="AEROMESH-SWARM | STAGE 1 VERIFICATION", dark=False):
        # Category / Kicker
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.35))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        tf_cat.margin_left = tf_cat.margin_top = tf_cat.margin_right = tf_cat.margin_bottom = 0
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.size = Pt(10)
        p_cat.font.bold = True
        p_cat.font.color.rgb = C_ACCENT if dark else C_ACCENT

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.733), Inches(0.6))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(22)
        p_title.font.bold = True
        p_title.font.color.rgb = C_TEXT_LIGHT if dark else C_PRIMARY

    def add_card(slide, left, top, width, height, bg_color=C_CARD_BG, border_color=C_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        if border_color:
            card.line.color.rgb = border_color
            card.line.width = Pt(1)
        else:
            card.line.fill.background()
        return card

    # =========================================================================
    # SLIDE 1: Title Slide (Dark Theme)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s1, C_BG_DARK)

    # Accent bar
    bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.5), Inches(0.15), Inches(4.5))
    bar.fill.solid()
    bar.fill.fore_color.rgb = C_ACCENT
    bar.line.fill.background()

    # Track badge
    badge = add_card(s1, Inches(1.2), Inches(1.5), Inches(6.5), Inches(0.4), bg_color=C_CARD_DARK, border_color=C_ACCENT)
    tb_badge = s1.shapes.add_textbox(Inches(1.3), Inches(1.55), Inches(6.3), Inches(0.3))
    tf_b = tb_badge.text_frame
    p_b = tf_b.paragraphs[0]
    p_b.text = "PUSHPAK GRAND CHALLENGE 2026 | TECHFEST, IIT BOMBAY"
    p_b.font.size = Pt(10)
    p_b.font.bold = True
    p_b.font.color.rgb = C_ACCENT

    # Main Title
    tb_main = s1.shapes.add_textbox(Inches(1.2), Inches(2.1), Inches(11.0), Inches(2.2))
    tf_m = tb_main.text_frame
    tf_m.word_wrap = True
    p1 = tf_m.paragraphs[0]
    p1.text = "AeroMesh-Swarm"
    p1.font.size = Pt(40)
    p1.font.bold = True
    p1.font.color.rgb = RGBColor(255, 255, 255)

    p2 = tf_m.add_paragraph()
    p2.text = "Resilient Multi-Hop UAV Swarm for Autonomous BVLOS Disaster Reconnaissance & Aerial Mesh Communication"
    p2.font.size = Pt(18)
    p2.font.color.rgb = C_ACCENT_BLUE
    p2.space_before = Pt(8)

    p3 = tf_m.add_paragraph()
    p3.text = "Stage 1: Preliminary Design Verification & Complete Simulation Proof-of-Concept"
    p3.font.size = Pt(14)
    p3.font.color.rgb = C_TEXT_LIGHT
    p3.space_before = Pt(6)

    # Info card
    card_info = add_card(s1, Inches(1.2), Inches(4.7), Inches(11.0), Inches(1.5), bg_color=C_CARD_DARK, border_color=RGBColor(40, 70, 105))
    tb_info = s1.shapes.add_textbox(Inches(1.5), Inches(4.85), Inches(10.4), Inches(1.2))
    tf_i = tb_info.text_frame
    tf_i.word_wrap = True

    p_i1 = tf_i.paragraphs[0]
    p_i1.text = "Author / Developer: Naga Surya Dinesh (Solo Developer)"
    p_i1.font.size = Pt(13)
    p_i1.font.bold = True
    p_i1.font.color.rgb = RGBColor(255, 255, 255)

    p_i2 = tf_i.add_paragraph()
    p_i2.text = "GitHub: github.com/nsd-surya-dinesh/aeromesh-swarm-disaster-response  |  Tag: v1.0.0-stage1"
    p_i2.font.size = Pt(11)
    p_i2.font.color.rgb = C_ACCENT_BLUE
    p_i2.space_before = Pt(4)

    p_i3 = tf_i.add_paragraph()
    p_i3.text = "Submission Target: pushpak_gc2026@aero.iitb.ac.in  |  Status: 100% Verified (19/19 Tests Passed)"
    p_i3.font.size = Pt(11)
    p_i3.font.color.rgb = C_TEXT_LIGHT
    p_i3.space_before = Pt(4)


    # =========================================================================
    # SLIDE 2: Required Deliverables Mapping
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s2, C_BG_LIGHT)
    add_header(s2, "Stage 1 Deliverables: Complete Submission Compliance")

    deliverables = [
        ("1. 6–8 Page Technical Proposal", "docs/TECHNICAL_PROPOSAL.md", "Mathematical formulations (ITU-R LoS, Shannon capacity, kinematics), 4-tier architecture, and empirical benchmark analysis.", C_PRIMARY),
        ("2. Software Architecture", "docs/TECHNICAL_PROPOSAL.md, README.md", "Modular Python architecture + ROS 2 Humble bridge layer with standard topics, services, and MAVROS bridge.", C_PRIMARY),
        ("3. Proof-of-Concept Simulation", "run_simulation.py", "Discrete-event 3D simulator verifying 4 challenging disaster scenarios with 100% PoI coverage and zero crashes.", C_PRIMARY),
        ("4. Complete Source Code", "core/, comm/, swarm/, simulation/", "26 cleanly separated modules (~2,450 lines of Python), type hints, unit & integration tests, fully documented.", C_PRIMARY),
        ("5. Installation & Setup Guides", "docs/INSTALLATION.md, JUDGE_SETUP_GUIDE.md", "Single-command installation workflow with 5-minute quickstart for competition judges and evaluators.", C_PRIMARY),
        ("6. Demonstration Video / Media", "scenario_3_demo.gif, scenario_3_snapshots/", "High-resolution visual demo showcasing real-time survivor preemption and sub-2.1s self-healing recovery.", C_PRIMARY),
    ]

    for idx, (title, path, desc, col) in enumerate(deliverables):
        col_idx = idx % 2
        row_idx = idx // 2
        x = Inches(0.8 + col_idx * 5.95)
        y = Inches(1.5 + row_idx * 1.8)
        w = Inches(5.8)
        h = Inches(1.65)

        card = add_card(s2, x, y, w, h)

        # Header strip inside card
        tb = s2.shapes.add_textbox(x + Inches(0.2), y + Inches(0.15), w - Inches(0.4), h - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = C_ACCENT

        p_p = tf.add_paragraph()
        p_p.text = f"Artifact: {path}"
        p_p.font.size = Pt(9.5)
        p_p.font.bold = True
        p_p.font.color.rgb = C_PRIMARY
        p_p.space_before = Pt(2)

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(10)
        p_d.font.color.rgb = C_TEXT_DARK
        p_d.space_before = Pt(4)


    # =========================================================================
    # SLIDE 3: Problem Formulation & Operational Context
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s3, C_BG_LIGHT)
    add_header(s3, "Mission Problem Formulation & Disaster Challenges")

    # Left Column: Operational Scenario
    card_l = add_card(s3, Inches(0.8), Inches(1.5), Inches(5.8), Inches(5.4))
    tb_l = s3.shapes.add_textbox(Inches(1.0), Inches(1.7), Inches(5.4), Inches(5.0))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "Post-Disaster Operational Context"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    points_l = [
        ("Communication Breakdown: ", "Severe earthquakes/landslides sever cellular towers and fiber backhaul. GCS operates outside the hazard perimeter."),
        ("BVLOS Reconnaissance: ", "Points of Interest (PoIs) are dispersed over rugged 2km x 2km terrain with deep canyons causing Non-Line-of-Sight (NLoS) blockage."),
        ("Energy Constraints: ", "Battery-limited multicopters must balance flight velocity, hover power at relay points, and strict Return-to-Base (RTB) reserves."),
        ("Dynamic Hazards: ", "Real-time emergency events (new survivor clusters, sudden relay hardware failures, RF interference) require instantaneous swarm re-planning.")
    ]
    for bold_txt, norm_txt in points_l:
        p = tf_l.add_paragraph()
        p.space_before = Pt(10)
        r1 = p.add_run()
        r1.text = bold_txt
        r1.font.bold = True
        r1.font.size = Pt(11)
        r1.font.color.rgb = C_ACCENT
        r2 = p.add_run()
        r2.text = norm_txt
        r2.font.size = Pt(10.5)
        r2.font.color.rgb = C_TEXT_DARK

    # Right Column: AeroMesh-Swarm Solution
    card_r = add_card(s3, Inches(6.8), Inches(1.5), Inches(5.733), Inches(5.4))
    tb_r = s3.shapes.add_textbox(Inches(7.0), Inches(1.7), Inches(5.333), Inches(5.0))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    p = tf_r.paragraphs[0]
    p.text = "AeroMesh-Swarm Core Innovations"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    points_r = [
        ("Decentralized CBBA Auctioning: ", "Conflict-free consensus algorithm allocating PoIs based on marginal utility, distance detours, and remaining battery state."),
        ("Steiner-Point Relay Deployment: ", "Autonomous positioning of relay UAVs at geometric Steiner midpoints governed by Artificial Potential Fields (APF)."),
        ("ETX Multi-Hop Mesh Routing: ", "Dynamic Ad-hoc wireless graph routing minimizing Expected Transmission Count (ETX) and packet delivery latency."),
        ("Sub-2.1s Autonomous Self-Healing: ", "Heartbeat monitoring detects node faults, instantly promoting standby/scout UAVs to bridge severed mesh topologies.")
    ]
    for bold_txt, norm_txt in points_r:
        p = tf_r.add_paragraph()
        p.space_before = Pt(10)
        r1 = p.add_run()
        r1.text = bold_txt
        r1.font.bold = True
        r1.font.size = Pt(11)
        r1.font.color.rgb = C_ACCENT
        r2 = p.add_run()
        r2.text = norm_txt
        r2.font.size = Pt(10.5)
        r2.font.color.rgb = C_TEXT_DARK


    # =========================================================================
    # SLIDE 4: Mathematical Modeling & Physical Foundations
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s4, C_BG_LIGHT)
    add_header(s4, "Mathematical System Formulations & Physical Models")

    math_blocks = [
        ("1. ITU-R P.1411 Probabilistic LoS Model",
         "Elevation angle theta between nodes i and j determines Line-of-Sight probability:\n\n"
         "  P(LoS) = 1 / [ 1 + a * exp(-b(theta - a)) ]\n\n"
         "Path Loss incorporates free-space loss and log-normal shadow fading:\n"
         "  PL(d) = 20 log10(4*pi*fc*d / c) + eta_LoS/NLoS + X_sigma\n"
         "  SNR = P_tx + G_tx + G_rx - PL(d) - N_floor  >=  10 dB (Relay Thresh)"),

        ("2. Shannon Channel Capacity & ETX Routing",
         "Theoretical wireless link bandwidth is modeled dynamically via Shannon-Hartley:\n\n"
         "  C_ij = B * log2( 1 + 10^(SNR_ij / 10) )  [Mbps]\n\n"
         "Link routing metric balances packet delivery ratio (PDR) via ETX:\n"
         "  ETX_ij = 1 / (d_f * d_r) ~= 1 / PDR_ij\n"
         "Dijkstra's shortest path dynamically routes telemetry through min-ETX paths."),

        ("3. Aerodynamic Power & Battery Depletion",
         "Instantaneous power consumption combines hover, profile, and parasite drag:\n\n"
         "  P(t) = P_hover * [ c1 + c2*(v/v_cruise)^2 + c3*(v/v_cruise)^3 ] + P_sensor + P_rf\n\n"
         "Dynamic Return-to-Base (RTB) energy boundary guarantees zero crash:\n"
         "  E_safe,i(t) = [ P_cruise * (||p_i - p_gcs|| / v_cruise) / 3600 ] + E_reserve")
    ]

    for idx, (title, content) in enumerate(math_blocks):
        x = Inches(0.8 + idx * 3.95)
        y = Inches(1.5)
        w = Inches(3.8)
        h = Inches(5.4)

        add_card(s4, x, y, w, h)
        tb = s4.shapes.add_textbox(x + Inches(0.2), y + Inches(0.2), w - Inches(0.4), h - Inches(0.4))
        tf = tb.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = C_PRIMARY

        p_c = tf.add_paragraph()
        p_c.text = content
        p_c.font.size = Pt(10)
        p_c.font.color.rgb = C_TEXT_DARK
        p_c.space_before = Pt(8)


    # =========================================================================
    # SLIDE 5: 4-Tier Software Architecture
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s5, C_BG_LIGHT)
    add_header(s5, "4-Tier Modular Software Architecture")

    tiers = [
        ("Tier 1: Visualization & GCS Layer", "Real-Time Telemetry & Operations", [
            "60 FPS Pygame Tactical 2D/3D Display with packet animations",
            "FastAPI + WebSocket interactive browser dashboard",
            "Dynamic event console (inject emergency survivor, RF jamming, motor fault)",
            "Automated video & GIF export engine (Pillow / OpenCV)"
        ], C_ACCENT),
        ("Tier 2: Swarm Autonomy & Decision Layer", "Distributed Intelligence", [
            "Consensus-Based Bundle Algorithm (CBBA) distributed task allocator",
            "Artificial Potential Fields (APF) & Dubins 3D collision-free path planning",
            "Swarm Health Monitor & sub-2.1s self-healing topology engine",
            "Smart Battery Return-to-Base (RTB) & relay handoff coordinator"
        ], C_PRIMARY),
        ("Tier 3: Aerial Mesh & Relay Network Layer", "Communication-Aware Networking", [
            "ETX-Weighted Dijkstra & dynamic Ad-hoc routing engine",
            "Euclidean Steiner tree & APF relay positioning algorithm",
            "Packet queue manager with priority telemetry forwarding",
            "ITU-R P.1411 probabilistic Line-of-Sight (LoS) & fading channel model"
        ], C_PRIMARY),
        ("Tier 4: Environment & Kinodynamics Layer", "Physics & Energetics Engine", [
            "3D kinematic flight physics with wind vector disturbances",
            "Semi-empirical rotorcraft aerodynamic power dissipation model",
            "GCS multi-pad fast charging & battery replenishment logic",
            "0.1s synchronized discrete-event orchestrator"
        ], C_PRIMARY)
    ]

    for idx, (title, subtitle, items, col) in enumerate(tiers):
        y = Inches(1.5 + idx * 1.35)
        add_card(s5, Inches(0.8), y, Inches(11.733), Inches(1.2))

        # Left tag
        tb_t = s5.shapes.add_textbox(Inches(1.0), y + Inches(0.15), Inches(3.5), Inches(0.9))
        tf_t = tb_t.text_frame
        tf_t.word_wrap = True
        p1 = tf_t.paragraphs[0]
        p1.text = title
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = col

        p2 = tf_t.add_paragraph()
        p2.text = subtitle
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_TEXT_MUTED
        p2.space_before = Pt(2)

        # Right bullets
        tb_b = s5.shapes.add_textbox(Inches(4.7), y + Inches(0.1), Inches(7.6), Inches(1.0))
        tf_b = tb_b.text_frame
        tf_b.word_wrap = True
        for b_idx, item in enumerate(items):
            p = tf_b.paragraphs[0] if b_idx == 0 else tf_b.add_paragraph()
            p.text = f"• {item}"
            p.font.size = Pt(9.5)
            p.font.color.rgb = C_TEXT_DARK
            if b_idx > 0:
                p.space_before = Pt(1)


    # =========================================================================
    # SLIDE 6: Communication-Aware Autonomy & Self-Healing
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s6, C_BG_LIGHT)
    add_header(s6, "Decentralized CBBA Task Allocation & Self-Healing Protocol")

    # Column 1: CBBA Auctioning
    c1 = add_card(s6, Inches(0.8), Inches(1.5), Inches(5.8), Inches(5.4))
    tb_c1 = s6.shapes.add_textbox(Inches(1.0), Inches(1.7), Inches(5.4), Inches(5.0))
    tf_c1 = tb_c1.text_frame
    tf_c1.word_wrap = True

    p = tf_c1.paragraphs[0]
    p.text = "1. CBBA Energy Marginal Utility Scoring"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    p_body1 = tf_c1.add_paragraph()
    p_body1.text = (
        "Each UAV autonomously bids on task bundles without a centralized master.\n\n"
        "Marginal Insertion Score:\n"
        "  S_ij(k) = w_j * gamma^(T_arr / 60) - alpha * (Delta_d / 1000) - beta * (Delta_E / E_cap)\n\n"
        "Key Operational Behaviors:\n"
        "• Conflict-Free Convergence: Pairwise max-bid consensus over the mesh.\n"
        "• Battery-Constrained Bundling: Rejects distant PoIs if round-trip energy exceeds safe RTB.\n"
        "• Emergency Preemption: When a high-priority survivor (e.g. Priority 8.0) is injected, bids are immediately recalculated to preempt low-priority scouts."
    )
    p_body1.font.size = Pt(10.5)
    p_body1.font.color.rgb = C_TEXT_DARK
    p_body1.space_before = Pt(8)

    # Column 2: Self-Healing Protocol
    c2 = add_card(s6, Inches(6.8), Inches(1.5), Inches(5.733), Inches(5.4))
    tb_c2 = s6.shapes.add_textbox(Inches(7.0), Inches(1.7), Inches(5.333), Inches(5.0))
    tf_c2 = tb_c2.text_frame
    tf_c2.word_wrap = True

    p = tf_c2.paragraphs[0]
    p.text = "2. Sub-2.1s Autonomous Self-Healing"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    p_body2 = tf_c2.add_paragraph()
    p_body2.text = (
        "Relay nodes form single points of failure if unmanaged. AeroMesh-Swarm executes automated healing:\n\n"
        "Dynamic Replacement Score:\n"
        "  Score(u) = 0.4 / ||p_u - p_relay|| + 0.3 * SoC_u + 0.3 * I(STANDBY)\n\n"
        "Three-Phase Recovery Cycle:\n"
        "1. Failure Detection: Heartbeat loss exceeds tau_timeout = 3.0s.\n"
        "2. Candidate Dispatch: Standby/Scout with highest score is instantly promoted to relay coordinates.\n"
        "3. Seamless Handoff: Link routes update via ETX Dijkstra; zero telemetry packets dropped (100% PDR)."
    )
    p_body2.font.size = Pt(10.5)
    p_body2.font.color.rgb = C_TEXT_DARK
    p_body2.space_before = Pt(8)


    # =========================================================================
    # SLIDE 7: 4 Benchmark Simulation Scenarios
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s7, C_BG_LIGHT)
    add_header(s7, "Comprehensive Stage 1 Verification Scenarios")

    scenarios = [
        ("Scenario 1: Baseline Survey", "5 UAVs | 10 PoIs | 2km x 2km Area", [
            "Standard multi-UAV reconnaissance over open terrain.",
            "Validates decentralized CBBA task allocation & conflict resolution.",
            "Single-hop LoS mesh connectivity to GCS.",
            "Result: 100% PoI coverage in 289s; 101.7ms avg latency."
        ]),
        ("Scenario 2: Deep Canyon Obstacle", "6 UAVs | 8 Distant PoIs | Severe NLoS Blockage", [
            "Mountain ridge blocks direct GCS-to-PoI line-of-sight.",
            "Forces autonomous deployment of 3-hop Steiner relay chain.",
            "Dynamic ETX routing prevents packet loss over multi-hop links.",
            "Result: 100% PoI coverage; 100% PDR; 282.2ms latency."
        ]),
        ("Scenario 3: Dynamic Fault & Emergency", "6 UAVs | 8 PoIs | Sudden Node Crash + Emergency", [
            "Mid-mission discovery of high-priority survivor group at t=100s.",
            "Sudden hardware/motor failure of Relay-1 at t=180s.",
            "Swarm executes emergency preemption & 2.1s self-healing recovery.",
            "Result: 100% coverage; 0 lost packets; mission completed in 229s."
        ]),
        ("Scenario 4: Endurance & Battery Cycling", "8 UAVs | 16 Dispersed PoIs | Multi-Cycle Mission", [
            "Large-scale mission exceeding single-battery energy capacity.",
            "UAVs autonomously trigger RTB, cycle through GCS charging pads.",
            "Seamless relay handoff preserves continuous telemetry.",
            "Result: 16/16 PoIs surveyed in 351.9s; zero crash."
        ]),
    ]

    for idx, (title, sub, bullets) in enumerate(scenarios):
        col_idx = idx % 2
        row_idx = idx // 2
        x = Inches(0.8 + col_idx * 5.95)
        y = Inches(1.5 + row_idx * 2.7)
        w = Inches(5.8)
        h = Inches(2.55)

        add_card(s7, x, y, w, h)
        tb = s7.shapes.add_textbox(x + Inches(0.2), y + Inches(0.15), w - Inches(0.4), h - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = C_PRIMARY

        p_sub = tf.add_paragraph()
        p_sub.text = sub
        p_sub.font.size = Pt(9.5)
        p_sub.font.bold = True
        p_sub.font.color.rgb = C_ACCENT
        p_sub.space_before = Pt(2)

        for b in bullets:
            p_b = tf.add_paragraph()
            p_b.text = f"• {b}"
            p_b.font.size = Pt(9.5)
            p_b.font.color.rgb = C_TEXT_DARK
            p_b.space_before = Pt(2)


    # =========================================================================
    # SLIDE 8: Empirical Benchmark Results & Verification Matrix
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s8, C_BG_LIGHT)
    add_header(s8, "Empirical Benchmark Results (Stage 1 Verification)")

    # Left: Table
    card_tbl = add_card(s8, Inches(0.8), Inches(1.5), Inches(7.5), Inches(5.4))

    # Add Table Shape
    rows, cols = 9, 5
    table_shape = s8.shapes.add_table(rows, cols, Inches(1.0), Inches(1.7), Inches(7.1), Inches(5.0))
    table = table_shape.table

    # Column widths
    table.columns[0].width = Inches(2.3)
    table.columns[1].width = Inches(1.2)
    table.columns[2].width = Inches(1.2)
    table.columns[3].width = Inches(1.2)
    table.columns[4].width = Inches(1.2)

    headers = ["Metric", "S1: Baseline", "S2: Canyon", "S3: Fault", "S4: Endurance"]
    data = [
        ["PoI Coverage (%)", "100.0%", "100.0%", "100.0%", "100.0%"],
        ["Packet Delivery Ratio (PDR)", "100.0%", "100.0%", "100.0%", "100.0%"],
        ["Avg E2E Latency (ms)", "101.7 ms", "282.2 ms", "123.0 ms", "114.4 ms"],
        ["PoIs Surveyed", "10 / 10", "8 / 8", "8 / 8", "16 / 16"],
        ["Mission Duration (s)", "289.0 s", "256.0 s", "229.9 s", "351.9 s"],
        ["Energy Consumed (kWh)", "0.12 kWh", "0.14 kWh", "0.11 kWh", "0.18 kWh"],
        ["Survey Rate (PoI/min)", "2.1 /min", "1.9 /min", "2.1 /min", "2.7 /min"],
        ["Swarm Survival Rate (%)", "100.0%", "100.0%", "100.0%", "100.0%"],
    ]

    for c_idx, h in enumerate(headers):
        cell = table.cell(0, c_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_PRIMARY
        p = cell.text_frame.paragraphs[0]
        p.font.bold = True
        p.font.size = Pt(9.5)
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT

    for r_idx, row in enumerate(data):
        for c_idx, val in enumerate(row):
            cell = table.cell(r_idx + 1, c_idx)
            cell.text = val
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(240, 245, 250) if r_idx % 2 == 0 else RGBColor(255, 255, 255)
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(9.5)
            p.font.color.rgb = C_GREEN if "100.0%" in val else C_TEXT_DARK
            if "100.0%" in val or c_idx == 0:
                p.font.bold = True
            p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT

    # Right: Key Takeaways Card
    card_t = add_card(s8, Inches(8.5), Inches(1.5), Inches(4.033), Inches(5.4))
    tb_t = s8.shapes.add_textbox(Inches(8.7), Inches(1.7), Inches(3.633), Inches(5.0))
    tf_t = tb_t.text_frame
    tf_t.word_wrap = True

    p = tf_t.paragraphs[0]
    p.text = "Key Empirical Findings"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    findings = [
        ("100% Mission Completion: ", "All 42 total PoIs across 4 scenarios successfully surveyed."),
        ("Zero Packet Loss: ", "ETX-weighted routing maintained 100% PDR across single and multi-hop links."),
        ("Rapid Failure Recovery: ", "Autonomous self-healing restored disconnected mesh within 2.1 seconds."),
        ("Zero Battery Depletion Crashes: ", "Dynamic RTB boundaries successfully brought all UAVs to GCS before critical exhaustion.")
    ]
    for bold_txt, norm_txt in findings:
        p = tf_t.add_paragraph()
        p.space_before = Pt(12)
        r1 = p.add_run()
        r1.text = bold_txt
        r1.font.bold = True
        r1.font.size = Pt(10.5)
        r1.font.color.rgb = C_ACCENT
        r2 = p.add_run()
        r2.text = norm_txt
        r2.font.size = Pt(10)
        r2.font.color.rgb = C_TEXT_DARK


    # =========================================================================
    # SLIDE 9: ROS 2 Humble Integration & Stage 2 Roadmap
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s9, C_BG_LIGHT)
    add_header(s9, "ROS 2 Humble Architecture & Stage 2 Deployment Roadmap")

    # Left: ROS 2 Architecture
    card_ros = add_card(s9, Inches(0.8), Inches(1.5), Inches(5.8), Inches(5.4))
    tb_ros = s9.shapes.add_textbox(Inches(1.0), Inches(1.7), Inches(5.4), Inches(5.0))
    tf_ros = tb_ros.text_frame
    tf_ros.word_wrap = True

    p = tf_ros.paragraphs[0]
    p.text = "ROS 2 Humble Compliance (Stage 2 Ready)"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    p_ros = tf_ros.add_paragraph()
    p_ros.text = (
        "The Python simulation models map 1:1 to a production ROS 2 package:\n\n"
        "Package: aeromesh_swarm (ROS 2 Humble / Iron)\n\n"
        "Standard Published Topics:\n"
        "• /aeromesh/uav_{id}/pose (geometry_msgs/PoseStamped)\n"
        "• /aeromesh/uav_{id}/battery_state (sensor_msgs/BatteryState)\n"
        "• /aeromesh/network/topology (aeromesh_msgs/MeshTopology)\n"
        "• /aeromesh/network/link_quality (aeromesh_msgs/LinkQuality)\n\n"
        "Custom ROS 2 Services:\n"
        "• /aeromesh/task/allocate (aeromesh_srvs/AllocateTasks)\n"
        "• /aeromesh/mission/inject_poi (aeromesh_srvs/InjectEmergencyPoI)\n"
        "• /aeromesh/metrics/summary (aeromesh_srvs/GetMissionMetrics)"
    )
    p_ros.font.size = Pt(10)
    p_ros.font.color.rgb = C_TEXT_DARK
    p_ros.space_before = Pt(6)

    # Right: Stage 2 & Hardware Roadmap
    card_rd = add_card(s9, Inches(6.8), Inches(1.5), Inches(5.733), Inches(5.4))
    tb_rd = s9.shapes.add_textbox(Inches(7.0), Inches(1.7), Inches(5.333), Inches(5.0))
    tf_rd = tb_rd.text_frame
    tf_rd.word_wrap = True

    p = tf_rd.paragraphs[0]
    p.text = "Hardware-in-the-Loop (HITL) Roadmap"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    steps = [
        ("Phase 1: PX4 SITL & Gazebo Garden: ", "Bridge CBBA & MeshRouter nodes with PX4 Autopilot over MAVROS in 3D physics environment with realistic wind turbulence."),
        ("Phase 2: Hardware Companion Computers: ", "Deploy decentralized nodes onto Raspberry Pi 4 / NVIDIA Jetson Orin Nano companion computers running ROS 2 DDS."),
        ("Phase 3: Wireless Mesh Hardware: ", "Interface with physical 802.11s ad-hoc mesh transceivers or long-range ESP-NOW / LoRa backup links."),
        ("Phase 4: Field Validation: ", "Execute autonomous multi-UAV disaster field trials with automated survivor tagging via YOLOv8-nano.")
    ]
    for bold_txt, norm_txt in steps:
        p = tf_rd.add_paragraph()
        p.space_before = Pt(10)
        r1 = p.add_run()
        r1.text = bold_txt
        r1.font.bold = True
        r1.font.size = Pt(10.5)
        r1.font.color.rgb = C_ACCENT
        r2 = p.add_run()
        r2.text = norm_txt
        r2.font.size = Pt(10)
        r2.font.color.rgb = C_TEXT_DARK


    # =========================================================================
    # SLIDE 10: Judge Setup & Verification Workflow
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s10, C_BG_LIGHT)
    add_header(s10, "5-Minute Quickstart & Verification Workflow for Evaluators")

    steps_eval = [
        ("Step 1: Clone & Install (1 min)", "pip install -r requirements.txt", "Zero heavy proprietary dependencies. Compatible with Linux, macOS, and Windows 10/11."),
        ("Step 2: Run Test Suite (30 sec)", "python -m pytest tests/ -v", "Executes all 19 unit & integration tests covering RF channel, CBBA, routing, and scenarios. (100% Pass)"),
        ("Step 3: Run Benchmarks (3 min)", "python run_simulation.py --benchmark-all", "Executes all 4 disaster scenarios in 10x real-time and prints full performance comparison matrix."),
        ("Step 4: Verify ROS 2 Bridge (10 sec)", "python ros2_interface/ros2_bridge.py", "Validates ROS 2 Humble node interface compliance and topic/service mappings for Stage 2."),
        ("Step 5: Inspect Visual Demo", "scenario_3_demo.gif", "Review high-resolution self-healing animation demonstrating autonomous 2.1s relay recovery."),
        ("Step 6: Review Technical Proposal", "docs/TECHNICAL_PROPOSAL.md", "Read complete 6-8 page academic proposal with complete mathematical formulations.")
    ]

    for idx, (step_title, cmd, note) in enumerate(steps_eval):
        col_idx = idx % 2
        row_idx = idx // 2
        x = Inches(0.8 + col_idx * 5.95)
        y = Inches(1.5 + row_idx * 1.8)
        w = Inches(5.8)
        h = Inches(1.65)

        add_card(s10, x, y, w, h)
        tb = s10.shapes.add_textbox(x + Inches(0.2), y + Inches(0.12), w - Inches(0.4), h - Inches(0.24))
        tf = tb.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = step_title
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = C_PRIMARY

        p_cmd = tf.add_paragraph()
        p_cmd.text = f"$ {cmd}"
        p_cmd.font.size = Pt(10)
        p_cmd.font.bold = True
        p_cmd.font.color.rgb = C_ACCENT
        p_cmd.space_before = Pt(3)

        p_note = tf.add_paragraph()
        p_note.text = note
        p_note.font.size = Pt(9.5)
        p_note.font.color.rgb = C_TEXT_DARK
        p_note.space_before = Pt(3)


    # =========================================================================
    # SLIDE 11: Summary & Stage 1 Conclusion (Dark Theme)
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s11, C_BG_DARK)

    # Header
    add_header(s11, "AeroMesh-Swarm: Stage 1 Verification Summary", dark=True)

    # 4 Highlights in Columns
    highlights = [
        ("100%", "Mission PoI Coverage", "All 42 PoIs surveyed across 4 disaster scenarios with zero unvisited targets.", C_ACCENT),
        ("100%", "Packet Delivery Ratio", "Zero telemetry loss over dynamic ETX multi-hop mesh routes (up to 3 hops).", C_ACCENT_BLUE),
        ("< 2.1s", "Self-Healing Recovery", "Autonomous relay failure detection & role promotion restoring network bridge.", C_GREEN),
        ("100%", "Swarm Survival Rate", "Dynamic RTB boundaries guarantee zero UAV crashes from battery depletion.", RGBColor(255, 193, 7))
    ]

    for idx, (stat, label, desc, col) in enumerate(highlights):
        x = Inches(0.8 + idx * 2.98)
        y = Inches(1.5)
        w = Inches(2.8)
        h = Inches(3.2)

        add_card(s11, x, y, w, h, bg_color=C_CARD_DARK, border_color=col)
        tb = s11.shapes.add_textbox(x + Inches(0.15), y + Inches(0.2), w - Inches(0.3), h - Inches(0.4))
        tf = tb.text_frame
        tf.word_wrap = True

        p_stat = tf.paragraphs[0]
        p_stat.text = stat
        p_stat.font.size = Pt(28)
        p_stat.font.bold = True
        p_stat.font.color.rgb = col
        p_stat.alignment = PP_ALIGN.CENTER

        p_lbl = tf.add_paragraph()
        p_lbl.text = label
        p_lbl.font.size = Pt(11)
        p_lbl.font.bold = True
        p_lbl.font.color.rgb = RGBColor(255, 255, 255)
        p_lbl.alignment = PP_ALIGN.CENTER
        p_lbl.space_before = Pt(6)

        p_desc = tf.add_paragraph()
        p_desc.text = desc
        p_desc.font.size = Pt(9.5)
        p_desc.font.color.rgb = C_TEXT_LIGHT
        p_desc.alignment = PP_ALIGN.CENTER
        p_desc.space_before = Pt(8)

    # Bottom Contact Card
    card_bot = add_card(s11, Inches(0.8), Inches(5.0), Inches(11.733), Inches(1.8), bg_color=C_CARD_DARK, border_color=C_PRIMARY)
    tb_bot = s11.shapes.add_textbox(Inches(1.1), Inches(5.15), Inches(11.133), Inches(1.5))
    tf_bot = tb_bot.text_frame
    tf_bot.word_wrap = True

    p = tf_bot.paragraphs[0]
    p.text = "Thank You! — Ready for Stage 1 Evaluation & Stage 2 Hardware Transition"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)

    p_info = tf_bot.add_paragraph()
    p_info.text = (
        "Author: Naga Surya Dinesh (Solo Developer)  |  Email: nagasuryadinesh@gmail.com  |  Affiliation: Autonomous Robotics & Swarm Lab\n"
        "Repository: https://github.com/nsd-surya-dinesh/aeromesh-swarm-disaster-response\n"
        "Submission Target: pushpak_gc2026@aero.iitb.ac.in  |  Pushpak Grand Challenge 2026, Techfest IIT Bombay"
    )
    p_info.font.size = Pt(11)
    p_info.font.color.rgb = C_ACCENT_BLUE
    p_info.space_before = Pt(6)

    output_path = "AeroMesh_Swarm_Stage1_Presentation.pptx"
    prs.save(output_path)
    print(f"[+] Successfully generated presentation: {output_path} (11 slides)")

if __name__ == "__main__":
    create_presentation()
