import Image from "next/image";
import Link from "next/link";
import LocationOnOutlinedIcon from "@mui/icons-material/LocationOnOutlined";
import PhoneOutlinedIcon from "@mui/icons-material/PhoneOutlined";
import EmailOutlinedIcon from "@mui/icons-material/EmailOutlined";
import FacebookIcon from "@mui/icons-material/Facebook";
import TwitterIcon from "@mui/icons-material/Twitter";
import YouTubeIcon from "@mui/icons-material/YouTube";
import PinterestIcon from "@mui/icons-material/Pinterest";
import InstagramIcon from "@mui/icons-material/Instagram";

import styles from "./landing-page.module.css";

type PageKey =
  | "home"
  | "dss"
  | "synthetic"
  | "ticosa"
  | "about"
  | "company"
  | "contact"
  | "subscription"
  | "payment";

type SolutionPageKey = "dss" | "synthetic" | "ticosa";

const navItems: Array<{ key: PageKey; label: string; href: string }> = [
  { key: "home", label: "Home", href: "/" },
  { key: "dss", label: "Infomentica DSS", href: "/landing-page/dss" },
  { key: "synthetic", label: "Employees", href: "/landing-page/synthetic" },
  { key: "ticosa", label: "TICOSA", href: "/landing-page/ticosa" },
  { key: "about", label: "About Us", href: "/landing-page/about" },
  { key: "company", label: "Company", href: "/landing-page/company" },
  { key: "contact", label: "Contact Us", href: "/landing-page/contact" },
];

const solutionCards = [
  {
    key: "dss",
    icon: "D",
    title: "Infomentica DSS",
    description:
      "AI Decision Support System for proposal intelligence, risk tracking, procurement insights and executive dashboards.",
    href: "/landing-page/dss",
    cta: "Learn More",
  },
  {
    key: "synthetic",
    icon: "S",
    title: "AI Synthetic Employees",
    description:
      "Syncora/Cyncora digital employees that handle repeatable knowledge work, triage, follow-ups and reporting.",
    href: "/landing-page/synthetic",
    cta: "Learn More",
  },
  {
    key: "ticosa",
    icon: "T",
    title: "AI Time Compression Systems",
    description:
      "TICOSA compresses long business workflows by automating analysis, drafting, review and decision preparation.",
    href: "/landing-page/ticosa",
    cta: "Learn More",
  },
];

const plans = [
  {
    tag: "Starter",
    price: "₹499",
    priceSuffix: "/ user / month",
    description: "For small teams starting with AI search and decision briefs.",
    features: ["Core dashboard", "Basic RAG search", "Email support"],
  },
  {
    tag: "Professional",
    price: "₹999",
    priceSuffix: "/ user / month",
    description: "For teams needing workflows, reports and synthetic task support.",
    features: ["Advanced DSS", "Workflow automation", "Role-based access"],
    featured: true,
    href: "/landing-page/subscription",
  },
  {
    tag: "Business",
    price: "₹1,999",
    priceSuffix: "/ user / month",
    description: "For departments managing multiple sources and AI employees.",
    features: ["Multi-repository AI", "Synthetic employee packs", "Analytics suite"],
  },
  {
    tag: "Enterprise",
    price: "Custom",
    description: "For regulated, multi-tenant and high-security enterprise setups.",
    features: ["Custom integrations", "Private deployment", "SLA support"],
  },
];

const solutionPageContent: Record<
  SolutionPageKey,
  {
    breadcrumb: string;
    title: string;
    subtitle: string;
    panelTitle: string;
    panelText: string;
    bullets: string[];
    features: Array<{ title: string; description: string }>;
  }
> = {
  dss: {
    breadcrumb: "AUGMIS / Solution",
    title: "Infomentica DSS",
    subtitle: "Enterprise AI Decision Support System for smarter management decisions.",
    panelTitle: "Turn enterprise information into decision-ready intelligence.",
    panelText:
      "Infomentica DSS helps teams search, summarize, compare and act on business documents, proposals, vendor records, procurement data and project updates.",
    bullets: [
      "AI-powered proposal and tender intelligence",
      "Vendor, supplier and contract risk insights",
      "Executive summaries and escalation tracking",
    ],
    features: [
      { title: "Semantic Search", description: "Find answers across PDFs, Excel, SharePoint and repository content." },
      { title: "RAG Copilot", description: "Ask questions and receive source-grounded business responses." },
      { title: "Risk Signals", description: "Detect gaps, overdue actions and procurement bottlenecks." },
      { title: "Dashboards", description: "Management-level insights with clean visual summaries." },
    ],
  },
  synthetic: {
    breadcrumb: "AUGMIS / Solution",
    title: "AI Synthetic Employees",
    subtitle: "Syncora/Cyncora digital workers for repetitive enterprise knowledge tasks.",
    panelTitle: "Deploy AI employees that work with your business systems.",
    panelText:
      "AI Synthetic Employees can monitor queues, prepare drafts, summarize documents, follow up on pending items and assist users through conversational workflows.",
    bullets: [
      "AI assistant roles for HR, procurement, projects and support",
      "Task execution with human review controls",
      "Audit trail, escalation and approval-ready outputs",
    ],
    features: [
      { title: "Syncora", description: "Synchronized AI worker for operational coordination." },
      { title: "Cyncora", description: "Conversational AI worker for user-facing productivity." },
      { title: "Role Packs", description: "Pre-built job roles for common business functions." },
      { title: "Human-in-Control", description: "Approvals remain with business users and managers." },
    ],
  },
  ticosa: {
    breadcrumb: "AUGMIS / Solution",
    title: "TICOSA",
    subtitle: "AI Time Compression Systems for reducing long business cycles.",
    panelTitle: "Compress work that normally takes days into structured AI-assisted cycles.",
    panelText:
      "TICOSA accelerates information gathering, review, drafting, comparison, analysis and decision preparation across complex business workflows.",
    bullets: [
      "Compress proposal, report and review preparation time",
      "Automate repetitive analysis and document comparison",
      "Standardize workflows from input to decision pack",
    ],
    features: [
      { title: "Workflow Acceleration", description: "Move faster from document intake to decision summary." },
      { title: "AI Review Loops", description: "Draft, compare, refine and validate outputs quickly." },
      { title: "Decision Packs", description: "Generate management-ready briefs and action trackers." },
      { title: "Time Analytics", description: "Measure cycle time reduction and bottleneck patterns." },
    ],
  },
};

function Navigation({ currentPage }: { currentPage: PageKey }) {
  return (
    <header className={styles.header}>
      <div className={styles.headerRail}>
        <div className={styles.headerRailInner}>
          <div className={styles.headerRailContacts}>
            <span className={styles.headerRailItem}>
              <LocationOnOutlinedIcon className={styles.headerRailIcon} fontSize="inherit" />
              AUGMIS, Jyoti Pride, Chakala, Andheri-E, Mumbai 400093
            </span>
            <span className={styles.headerRailItem}>
              <PhoneOutlinedIcon className={styles.headerRailIcon} fontSize="inherit" />
              +966531815726 / +917738423517
            </span>
            <span className={styles.headerRailItem}>
              <EmailOutlinedIcon className={styles.headerRailIcon} fontSize="inherit" />
              info@augmis.com
            </span>
          </div>

          <div className={styles.headerRailSocials} aria-label="Social media placeholders">
            <FacebookIcon className={styles.headerRailSocialIcon} fontSize="small" />
            <TwitterIcon className={styles.headerRailSocialIcon} fontSize="small" />
            <YouTubeIcon className={styles.headerRailSocialIcon} fontSize="small" />
            <PinterestIcon className={styles.headerRailSocialIcon} fontSize="small" />
            <InstagramIcon className={styles.headerRailSocialIcon} fontSize="small" />
          </div>
        </div>
      </div>
      <div className={styles.container}>
        <div className={styles.nav}>
          <Link href="/" className={styles.brand}>
            <Image
              src="/augmis-logocombined-26june2026.png"
              alt="AUGMIS logo"
              width={247}
              height={55}
              className={styles.brandLogo}
            />
          </Link>

          <nav className={styles.navActions}>
            {navItems.map((item) => (
              <Link
                key={item.key}
                href={item.href}
                className={`${styles.navLink} ${currentPage === item.key ? styles.navLinkActive : ""}`}
              >
                {item.label}
              </Link>
            ))}
            <Link href="/login?redirectTo=/home" className={styles.loginButton}>
              Login
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}

function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.container}>
        <div className={styles.footerGrid}>
          <div>
            <Link href="/" className={styles.brand}>
              <Image
                src="/augmis-logocombined-26june2026.png"
                alt="AUGMIS logo"
                width={247}
                height={55}
                className={styles.brandLogo}
              />
            </Link>
            <p className={styles.footerBrandText}>
              Corporate SaaS solutions for AI-powered decisions, synthetic workforce automation and time compression.
            </p>
          </div>

          <div>
            <h4>Solutions</h4>
            <Link href="/landing-page/dss" className={styles.footerLink}>Infomentica DSS</Link>
            <Link href="/landing-page/synthetic" className={styles.footerLink}>AI Synthetic Employees</Link>
            <Link href="/landing-page/ticosa" className={styles.footerLink}>TICOSA</Link>
          </div>

          <div>
            <h4>Company</h4>
            <Link href="/landing-page/about" className={styles.footerLink}>About Us</Link>
            <Link href="/landing-page/company" className={styles.footerLink}>Company</Link>
            <Link href="/landing-page/contact" className={styles.footerLink}>Contact</Link>
          </div>

          <div>
            <h4>Legal</h4>
            <span className={styles.footerLink}>Privacy Policy</span>
            <span className={styles.footerLink}>Terms of Service</span>
            <span className={styles.footerLink}>Security</span>
          </div>
        </div>

        <div className={styles.bottomBar}>
          <span>© 2026 AUGMIS. All rights reserved.</span>
          <span>AI Augmented Information Systems</span>
        </div>
      </div>
    </footer>
  );
}

function HomePageBody() {
  return (
    <>
      <section className={styles.hero}>
        <div className={styles.container}>
          <div className={styles.heroContent}>
            <div className={styles.eyebrow}>Enterprise AI Solutions</div>
            <h1 className={styles.heroTitle}>
              AI-augmented systems
              <br />
              for faster decisions, smarter teams and
              <br />
              compressed execution cycles.
            </h1>
            <p className={styles.heroText}>
              AUGMIS brings together Decision Support, Synthetic Employees
              <br />
              and Time Compression Systems into one corporate AI transformation portfolio.
            </p>
          </div>
        </div>
      </section>

      <section className={styles.ctaBand}>
        <div className={`${styles.container} ${styles.ctaBandInner}`}>
          <div className={styles.ctaBandText}>
            <h2>Need faster enterprise decisions with AI you can trust?</h2>
            <p>
              Start with AUGMIS to unify decision support, synthetic employees and time compression workflows in one platform.
            </p>
          </div>
          <Link href="/register" className={styles.ctaBandButton}>
            Start For Free
          </Link>
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.container}>
          <div className={styles.sectionTitle}>
            <h2>Solution Briefs</h2>
            <p>
              Focused AI products designed to solve practical enterprise information, workforce and execution bottlenecks.
            </p>
          </div>
          <div className={styles.cards}>
            {solutionCards.map((card) => (
              <div
                key={card.title}
                className={`${styles.card} ${card.key === "dss" ? styles.cardDss : ""} ${card.key === "synthetic" ? styles.cardSynthetic : ""} ${card.key === "ticosa" ? styles.cardTicosa : ""}`}
              >
                <div className={styles.icon}>{card.icon}</div>
                <h3>{card.title}</h3>
                <p>{card.description}</p>
                <Link href={card.href} className={styles.buttonDark}>
                  {card.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.consultingSection}>
        <div className={styles.consultingGrid}>
          <div className={styles.consultingCopy}>
            <div className={styles.consultingEyebrow}>AUGMIS CONSULTING</div>
            <h2>Design the right AUGMIS rollout for your teams, repositories and workflows.</h2>
            <p>
              We help enterprise and growth-stage teams map the right mix of Infomentica DSS,
              AI Synthetic Employees and TICOSA so you can improve decision quality, reduce manual effort,
              and compress execution time without overcomplicating adoption.
            </p>
            <Link href="/landing-page/contact" className={styles.consultingButton}>
              Request Consultation
            </Link>
          </div>

          <div className={styles.consultingVisual} aria-hidden="true" />
        </div>
      </section>

      <section id="plans" className={`${styles.section} ${styles.sectionMuted}`}>
        <div className={styles.container}>
          <div className={styles.sectionTitle}>
            <h2>Subscription Plans</h2>
            <p>Simple SaaS plans for pilot teams, growing companies and enterprise-wide AI adoption.</p>
          </div>
          <div className={styles.plans}>
            {plans.map((plan) => (
              <div
                key={plan.tag}
                className={`${styles.plan} ${plan.featured ? styles.planFeatured : ""}`}
              >
                <span className={styles.tag}>{plan.tag}</span>
                <div className={styles.price}>
                  {plan.price}{" "}
                  {plan.priceSuffix ? <span className={styles.priceSmall}>{plan.priceSuffix}</span> : null}
                </div>
                <p>{plan.description}</p>
                <ul>
                  {plan.features.map((feature) => (
                    <li key={feature}>{feature}</li>
                  ))}
                </ul>
                {plan.href ? (
                  <Link href={plan.href} className={styles.planButton}>
                    View Offer
                  </Link>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}

function SolutionPageBody({ page }: { page: SolutionPageKey }) {
  const content = solutionPageContent[page];

  return (
    <>
      <section className={styles.pageHero}>
        <div className={styles.container}>
          <div className={styles.breadcrumb}>{content.breadcrumb}</div>
          <h1>{content.title}</h1>
          <p>{content.subtitle}</p>
        </div>
      </section>

      <section className={styles.section}>
        <div className={`${styles.container} ${styles.split}`}>
          <div className={styles.panel}>
            <h2>{content.panelTitle}</h2>
            <p className={styles.panelText}>{content.panelText}</p>
            <div className={styles.list}>
              {content.bullets.map((bullet) => (
                <div key={bullet} className={styles.listItem}>
                  <span className={styles.tick}>✓</span>
                  <span>{bullet}</span>
                </div>
              ))}
            </div>
          </div>

          <div className={styles.featureGrid}>
            {content.features.map((feature) => (
              <div key={feature.title} className={styles.feature}>
                <h4>{feature.title}</h4>
                <p>{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}

function AboutPageBody() {
  return (
    <>
      <section className={styles.pageHero}>
        <div className={styles.container}>
          <div className={styles.breadcrumb}>AUGMIS</div>
          <h1>About Us</h1>
          <p>We build practical AI systems for information-heavy organizations.</p>
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.container}>
          <div className={styles.panel}>
            <h2>Our Purpose</h2>
            <p className={styles.panelText}>
              AUGMIS stands for AI Augmented Information Systems. The name fits well: it clearly positions the company around AI-enhanced enterprise information, decision support and operational intelligence.
            </p>
            <p className={styles.panelText}>
              Our focus is to help businesses convert scattered information into structured decisions, reliable workflows and measurable productivity improvement.
            </p>
          </div>
        </div>
      </section>
    </>
  );
}

function CompanyPageBody() {
  const items = [
    {
      icon: "M",
      title: "Mission",
      description: "To make enterprise AI adoption simple, useful and decision-focused.",
    },
    {
      icon: "V",
      title: "Vision",
      description: "To become a trusted AI systems partner for growing businesses and enterprise teams.",
    },
    {
      icon: "P",
      title: "Principles",
      description: "Security, clarity, accountability, human control and measurable business impact.",
    },
  ];

  return (
    <>
      <section className={styles.pageHero}>
        <div className={styles.container}>
          <div className={styles.breadcrumb}>AUGMIS</div>
          <h1>Company</h1>
          <p>Corporate profile and operating philosophy.</p>
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.container}>
          <div className={styles.cards}>
            {items.map((item) => (
              <div key={item.title} className={styles.card}>
                <div className={styles.icon}>{item.icon}</div>
                <h3>{item.title}</h3>
                <p>{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}

function ContactPageBody() {
  return (
    <>
      <section className={styles.pageHero}>
        <div className={styles.container}>
          <div className={styles.breadcrumb}>AUGMIS</div>
          <h1>Contact Us</h1>
          <p>Start a conversation about your AI transformation roadmap.</p>
        </div>
      </section>

      <section className={styles.section}>
        <div className={`${styles.container} ${styles.contactGrid}`}>
          <div className={styles.contactInfo}>
            <h2>Get in touch</h2>
            <p><strong>Email:</strong> contact@augmis.ai</p>
            <p><strong>Phone:</strong> +91-00000-00000</p>
            <p><strong>Office:</strong> India / GCC Operations</p>
            <p className={styles.contactMeta}>
              Replace these details with your official contact information before publishing.
            </p>
          </div>

          <form className={styles.contactForm}>
            <input className={styles.formField} placeholder="Full Name" />
            <input className={styles.formField} placeholder="Business Email" type="email" />
            <select className={styles.formSelect} defaultValue="Infomentica DSS">
              <option>Infomentica DSS</option>
              <option>AI Synthetic Employees</option>
              <option>TICOSA</option>
              <option>Enterprise Consultation</option>
            </select>
            <textarea className={styles.formTextarea} placeholder="Tell us about your requirement" />
            <button type="button" className={styles.buttonDark}>
              Submit Enquiry
            </button>
          </form>
        </div>
      </section>
    </>
  );
}

function SubscriptionPageBody() {
  return (
    <>
      <section className={styles.pageHero}>
        <div className={styles.container}>
          <div className={styles.breadcrumb}>AUGMIS / Subscription</div>
          <h1>Professional Subscription</h1>
          <p>Placeholder commercial page for the current AUGMIS offering and payment journey.</p>
        </div>
      </section>

      <section className={styles.section}>
        <div className={`${styles.container} ${styles.subscriptionGrid}`}>
          <div className={styles.panel}>
            <h2>One professional plan for early production teams.</h2>
            <p className={styles.panelText}>
              The current AUGMIS subscription offer is a single Professional plan designed for up to 3 users per month.
              It is intended for teams that want enterprise AI decision support, synthetic employee workflows and
              time-compression capabilities in one managed offering.
            </p>
            <div className={styles.list}>
              {[
                "Up to 3 named users per month",
                "Infomentica DSS access for document intelligence and decision support",
                "AI Synthetic Employees for repeatable knowledge work",
                "TICOSA workflow acceleration capabilities",
                "Placeholder page for now with payment routing ready",
              ].map((bullet) => (
                <div key={bullet} className={styles.listItem}>
                  <span className={styles.tick}>✓</span>
                  <span>{bullet}</span>
                </div>
              ))}
            </div>
          </div>

          <div className={styles.subscriptionCard}>
            <span className={styles.subscriptionTag}>Current Offer</span>
            <h3>Professional Plan</h3>
            <div className={styles.subscriptionPrice}>3 Users / Month</div>
            <p>
              This is a placeholder subscription page. Final billing rules, taxes, pricing display and payment gateway
              behavior can be connected next.
            </p>
            <Link href="/landing-page/payment" className={styles.subscriptionButton}>
              Subscribe
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}

function PaymentPageBody() {
  return (
    <>
      <section className={styles.pageHero}>
        <div className={styles.container}>
          <div className={styles.breadcrumb}>AUGMIS / Payment</div>
          <h1>Payment Page</h1>
          <p>Placeholder handoff screen for the Professional subscription checkout flow.</p>
        </div>
      </section>

      <section className={styles.section}>
        <div className={`${styles.container} ${styles.subscriptionGrid}`}>
          <div className={styles.panel}>
            <h2>Checkout integration placeholder.</h2>
            <p className={styles.panelText}>
              This page is where the payment workflow will be connected. For now it confirms the selected plan and
              provides a clear destination for the Subscribe button from the offering page.
            </p>
            <div className={styles.list}>
              {[
                "Selected plan: Professional",
                "Users included: 3 per month",
                "Next step: connect payment gateway or billing provider",
              ].map((bullet) => (
                <div key={bullet} className={styles.listItem}>
                  <span className={styles.tick}>✓</span>
                  <span>{bullet}</span>
                </div>
              ))}
            </div>
          </div>

          <div className={styles.subscriptionCard}>
            <span className={styles.subscriptionTag}>Ready For Integration</span>
            <h3>Professional Plan Checkout</h3>
            <div className={styles.subscriptionPrice}>3 Users / Month</div>
            <p>Replace this placeholder with your actual payment form, hosted checkout, or billing provider redirect.</p>
            <Link href="/landing-page/contact" className={styles.subscriptionButtonSecondary}>
              Contact Sales
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}

export function LandingPageContent({ currentPage }: { currentPage: PageKey }) {
  return (
    <div className={styles.page}>
      <Navigation currentPage={currentPage} />

      <main>
        {currentPage === "home" ? <HomePageBody /> : null}
        {currentPage === "dss" ? <SolutionPageBody page="dss" /> : null}
        {currentPage === "synthetic" ? <SolutionPageBody page="synthetic" /> : null}
        {currentPage === "ticosa" ? <SolutionPageBody page="ticosa" /> : null}
        {currentPage === "about" ? <AboutPageBody /> : null}
        {currentPage === "company" ? <CompanyPageBody /> : null}
        {currentPage === "contact" ? <ContactPageBody /> : null}
        {currentPage === "subscription" ? <SubscriptionPageBody /> : null}
        {currentPage === "payment" ? <PaymentPageBody /> : null}
      </main>

      <Footer />
    </div>
  );
}
