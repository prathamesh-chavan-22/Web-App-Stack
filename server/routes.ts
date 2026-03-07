import type { Express } from "express";
import type { Server } from "http";
import { storage } from "./storage";
import { api } from "@shared/routes";
import { insertSpeakingPracticeSchema } from "@shared/schema";
import { z } from "zod";
import session from "express-session";
import connectPg from "connect-pg-simple";
import { pool } from "./db";

// Simple unsecure auth for MVP purposes
// In a real application this would use Passport/JWT or Replit Auth
const SESSION_SECRET = process.env.SESSION_SECRET || "development_secret";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {

  const PgSession = connectPg(session);
  app.use(session({
    store: new PgSession({ pool, createTableIfMissing: true }),
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: { maxAge: 30 * 24 * 60 * 60 * 1000 } // 30 days
  }));

  // Seed DB Function
  async function seedDatabase() {
    try {
      const existingUsers = await storage.getUsers();
      if (existingUsers.length === 0) {
        console.log("Seeding database...");

        const lAndD = await storage.createUser({ email: "admin@lms.local", password: "password", fullName: "Admin User", role: "l_and_d" });
        const manager = await storage.createUser({ email: "manager@lms.local", password: "password", fullName: "Manager User", role: "manager" });
        const emp1 = await storage.createUser({ email: "employee@lms.local", password: "password", fullName: "John Employee", role: "employee" });
        const emp2 = await storage.createUser({ email: "jane.doe@lms.local", password: "password", fullName: "Jane Doe", role: "employee" });
        const emp3 = await storage.createUser({ email: "alex.kumar@lms.local", password: "password", fullName: "Alex Kumar", role: "employee" });

        // Course 1: Fundamentals of React
        const c1 = await storage.createCourse({ title: "Fundamentals of React", description: "Master the building blocks of modern web development with React. Learn components, state management, hooks, and best practices.", status: "published", createdBy: lAndD.id, depth: "beginner", objectives: ["Understand React components and JSX", "Manage state and props effectively", "Use React hooks for modern development"] });
        await storage.createCourseModule({ courseId: c1.id, title: "Components & JSX", content: "## What Are React Components?\n\nReact components are the fundamental building blocks of any React application. A component is a reusable piece of UI.", sortOrder: 1 });
        await storage.createCourseModule({ courseId: c1.id, title: "State & Props", content: "## Understanding Props\n\nProps are read-only inputs passed from a parent component to a child. They allow data to flow downward through the component tree.", sortOrder: 2 });
        await storage.createCourseModule({ courseId: c1.id, title: "React Hooks", content: "## Introduction to Hooks\n\nHooks are functions that let you hook into React features from functional components.", sortOrder: 3 });

        // Course 2: Python for Beginners
        const c2 = await storage.createCourse({ title: "Python for Beginners", description: "Start your programming journey with Python — one of the world's most popular and beginner-friendly languages.", status: "published", createdBy: lAndD.id, depth: "beginner", objectives: ["Write Python programs from scratch", "Understand data types and control flow", "Create reusable functions and modules"] });
        await storage.createCourseModule({ courseId: c2.id, title: "Variables & Data Types", content: "## Getting Started with Python\n\nPython is known for its clean, readable syntax. Variables store data values.", sortOrder: 1 });
        await storage.createCourseModule({ courseId: c2.id, title: "Control Flow", content: "## Making Decisions with Conditionals\n\nLearn if/elif/else, for loops, while loops, and list comprehensions.", sortOrder: 2 });
        await storage.createCourseModule({ courseId: c2.id, title: "Functions & Modules", content: "## Defining Functions\n\nFunctions are reusable blocks of code. Use def to define them.", sortOrder: 3 });

        // Course 3: Introduction to Data Science
        const c3 = await storage.createCourse({ title: "Introduction to Data Science", description: "Explore the data science workflow from data wrangling to visualization and machine learning basics.", status: "published", createdBy: lAndD.id, depth: "intermediate", objectives: ["Manipulate data with Pandas", "Create insightful visualizations", "Build basic ML models"] });
        await storage.createCourseModule({ courseId: c3.id, title: "Data Wrangling with Pandas", content: "## Introduction to Pandas\n\nPandas is the go-to library for data manipulation in Python.", sortOrder: 1 });
        await storage.createCourseModule({ courseId: c3.id, title: "Data Visualization", content: "## Visualizing Data\n\nGood visualizations tell stories. Python has powerful libraries for this.", sortOrder: 2 });

        // Course 4: Cloud Computing Essentials
        const c4 = await storage.createCourse({ title: "Cloud Computing Essentials", description: "Understand cloud computing concepts, major AWS services, and learn to deploy applications on the cloud.", status: "published", createdBy: lAndD.id, depth: "beginner", objectives: ["Understand cloud computing models", "Navigate core AWS services", "Deploy a basic application on the cloud"] });
        await storage.createCourseModule({ courseId: c4.id, title: "Cloud Concepts", content: "## What is Cloud Computing?\n\nCloud computing delivers computing resources over the internet on a pay-as-you-go basis.", sortOrder: 1 });
        await storage.createCourseModule({ courseId: c4.id, title: "AWS Core Services", content: "## Essential AWS Services\n\nEC2 for compute, S3 for storage, RDS for databases, Lambda for serverless.", sortOrder: 2 });
        await storage.createCourseModule({ courseId: c4.id, title: "Deploying on the Cloud", content: "## Deploying Your First Application\n\nContainerize with Docker, push to a registry, and deploy.", sortOrder: 3 });

        // Course 5: Cybersecurity Fundamentals
        const c5 = await storage.createCourse({ title: "Cybersecurity Fundamentals", description: "Learn to identify threats, secure networks, and follow security best practices.", status: "published", createdBy: lAndD.id, depth: "beginner", objectives: ["Identify common cyber threats", "Understand network security principles", "Implement security best practices"] });
        await storage.createCourseModule({ courseId: c5.id, title: "Threat Landscape", content: "## Understanding Cyber Threats\n\nCommon attacks include phishing, malware, SQL injection, DDoS, and man-in-the-middle.", sortOrder: 1 });
        await storage.createCourseModule({ courseId: c5.id, title: "Network Security", content: "## Securing Your Network\n\nFirewalls, encryption, VPNs, and Zero Trust Architecture.", sortOrder: 2 });
        await storage.createCourseModule({ courseId: c5.id, title: "Security Best Practices", content: "## Security Best Practices for Developers\n\nMFA, secure coding, OWASP Top 10, incident response.", sortOrder: 3 });

        // Enrollments with varied progress
        await storage.createEnrollment({ userId: emp1.id, courseId: c1.id, status: "in_progress", progressPct: 65 });
        await storage.createEnrollment({ userId: emp1.id, courseId: c2.id, status: "completed", progressPct: 100 });
        await storage.createEnrollment({ userId: emp2.id, courseId: c3.id, status: "in_progress", progressPct: 40 });
        await storage.createEnrollment({ userId: emp2.id, courseId: c4.id, status: "assigned", progressPct: 0 });
        await storage.createEnrollment({ userId: emp3.id, courseId: c5.id, status: "in_progress", progressPct: 80 });
        await storage.createEnrollment({ userId: emp3.id, courseId: c1.id, status: "in_progress", progressPct: 20 });

        // Notifications
        await storage.createNotification({ userId: emp1.id, title: "Welcome", message: "Welcome to the LMS! Start with Fundamentals of React.", isRead: false });
        await storage.createNotification({ userId: emp1.id, title: "Course Completed 🎉", message: "Congratulations! You have completed Python for Beginners.", isRead: false });
        await storage.createNotification({ userId: emp2.id, title: "New Course Assigned", message: "You have been assigned Cloud Computing Essentials.", isRead: false });
        await storage.createNotification({ userId: emp3.id, title: "Keep it up!", message: "You're 80% through Cybersecurity Fundamentals. Almost there!", isRead: false });

        console.log("Database seeded successfully with 5 fundamental courses.");
      }
    } catch (err) {
      console.error("Error seeding database:", err);
    }
  }

  // Auth Routes
  app.post(api.auth.login.path, async (req, res) => {
    try {
      const { email, password } = api.auth.login.input.parse(req.body);
      const user = await storage.getUserByEmail(email);

      // Simple MVP auth
      if (!user || user.password !== password) {
        return res.status(401).json({ message: "Invalid email or password" });
      }

      (req.session as any).userId = user.id;
      res.json(user);
    } catch (err) {
      if (err instanceof z.ZodError) {
        return res.status(400).json({ message: err.errors[0].message });
      }
      res.status(500).json({ message: "Internal error" });
    }
  });

  app.post(api.auth.register.path, async (req, res) => {
    try {
      const input = api.auth.register.input.parse(req.body);

      const existing = await storage.getUserByEmail(input.email);
      if (existing) {
        return res.status(400).json({ message: "User already exists", field: "email" });
      }

      const user = await storage.createUser(input);
      (req.session as any).userId = user.id;
      res.status(201).json(user);
    } catch (err) {
      if (err instanceof z.ZodError) {
        return res.status(400).json({ message: err.errors[0].message });
      }
      res.status(500).json({ message: "Internal error" });
    }
  });

  app.get(api.auth.me.path, async (req, res) => {
    const userId = (req.session as any).userId;
    if (!userId) {
      return res.status(401).json({ message: "Not authenticated" });
    }

    const user = await storage.getUser(userId);
    if (!user) {
      return res.status(401).json({ message: "Not authenticated" });
    }

    res.json(user);
  });

  app.post(api.auth.logout.path, (req, res) => {
    req.session.destroy(() => {
      res.json({ message: "Logged out" });
    });
  });

  // User Routes
  app.get(api.users.list.path, async (req, res) => {
    const users = await storage.getUsers();
    res.json(users);
  });

  // Course Routes
  app.get(api.courses.list.path, async (req, res) => {
    const courses = await storage.getCourses();
    res.json(courses);
  });

  app.post(api.courses.create.path, async (req, res) => {
    try {
      const input = api.courses.create.input.parse(req.body);
      // Ensure createdBy is set correctly by parsing it as a number
      const course = await storage.createCourse({ ...input, createdBy: input.createdBy ? Number(input.createdBy) : null });
      res.status(201).json(course);
    } catch (err) {
      if (err instanceof z.ZodError) {
        return res.status(400).json({ message: err.errors[0].message });
      }
      res.status(500).json({ message: "Internal error" });
    }
  });

  app.get(api.courses.get.path, async (req, res) => {
    const course = await storage.getCourse(Number(req.params.id));
    if (!course) {
      return res.status(404).json({ message: "Course not found" });
    }
    res.json(course);
  });

  app.get(api.courses.getModules.path, async (req, res) => {
    const modules = await storage.getCourseModules(Number(req.params.id));
    res.json(modules);
  });

  app.post(api.courses.createModule.path, async (req, res) => {
    try {
      const input = api.courses.createModule.input.parse(req.body);
      const module = await storage.createCourseModule({
        ...input,
        courseId: Number(req.params.id)
      });
      res.status(201).json(module);
    } catch (err) {
      if (err instanceof z.ZodError) {
        return res.status(400).json({ message: err.errors[0].message });
      }
      res.status(500).json({ message: "Internal error" });
    }
  });

  // Enrollment Routes
  app.get(api.enrollments.list.path, async (req, res) => {
    // If regular employee, only show their enrollments
    const userId = req.query.userId ? Number(req.query.userId) : undefined;
    const enrollments = await storage.getEnrollments(userId);
    res.json(enrollments);
  });

  app.post(api.enrollments.create.path, async (req, res) => {
    try {
      const input = api.enrollments.create.input.parse(req.body);
      const enrollment = await storage.createEnrollment({
        ...input,
        userId: Number(input.userId),
        courseId: Number(input.courseId)
      });
      res.status(201).json(enrollment);
    } catch (err) {
      if (err instanceof z.ZodError) {
        return res.status(400).json({ message: err.errors[0].message });
      }
      res.status(500).json({ message: "Internal error" });
    }
  });

  app.patch(api.enrollments.updateProgress.path, async (req, res) => {
    try {
      const input = api.enrollments.updateProgress.input.parse(req.body);
      const enrollment = await storage.updateEnrollmentProgress(Number(req.params.id), input);
      res.json(enrollment);
    } catch (err) {
      if (err instanceof z.ZodError) {
        return res.status(400).json({ message: err.errors[0].message });
      }
      res.status(404).json({ message: "Enrollment not found" });
    }
  });

  // Notification Routes
  app.get(api.notifications.list.path, async (req, res) => {
    const userId = (req.session as any).userId;
    if (!userId) return res.status(401).json({ message: "Not authenticated" });

    const notifications = await storage.getNotifications(userId);
    res.json(notifications);
  });

  app.patch(api.notifications.markRead.path, async (req, res) => {
    try {
      const notification = await storage.markNotificationRead(Number(req.params.id));
      res.json(notification);
    } catch (err) {
      res.status(404).json({ message: "Notification not found" });
    }
  });

  // Speaking Practice Routes
  app.get("/api/speaking", async (req, res) => {
    const userId = (req.session as any).userId;
    if (!userId) return res.status(401).json({ message: "Not authenticated" });
    const practices = await storage.getSpeakingPractices(userId);
    res.json(practices);
  });

  app.post("/api/speaking", async (req, res) => {
    try {
      const userId = (req.session as any).userId;
      if (!userId) return res.status(401).json({ message: "Not authenticated" });
      const data = insertSpeakingPracticeSchema.parse({ ...req.body, userId });
      const practice = await storage.createSpeakingPractice(data);
      res.status(201).json(practice);
    } catch (err) {
      if (err instanceof z.ZodError) {
        return res.status(400).json({ message: err.errors[0].message });
      }
      res.status(500).json({ message: "Internal error" });
    }
  });

  // Call seed DB
  seedDatabase();

  return httpServer;
}
