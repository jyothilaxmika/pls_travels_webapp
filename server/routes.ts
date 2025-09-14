import { Request, Response, Router } from "express";
import { z } from "zod";
import path from "path";
import { fileURLToPath } from "url";
import { sendOTPSchema, verifyOTPSchema, resendOTPSchema, insertDriverProfileSchema, DriverStatus } from "@shared/schema";
import multer from "multer";
import { mkdirSync } from "fs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Role guard middleware functions
function requireAuth(req: any, res: any, next: any) {
  if (!req.session?.user) {
    return res.redirect('/auth/login');
  }
  next();
}

function requireRole(roles: string[]) {
  return (req: any, res: any, next: any) => {
    if (!req.session?.user) {
      return res.redirect('/auth/login');
    }
    
    if (!roles.includes(req.session.user.role)) {
      return res.status(403).send(`
        <html>
          <head><title>Access Denied</title></head>
          <body>
            <h1>Access Denied</h1>
            <p>You don't have permission to access this page.</p>
            <a href="/auth/login">Login</a>
          </body>
        </html>
      `);
    }
    next();
  };
}

export function registerRoutes(app: any) {
  const router = Router();

  // Root route - redirect to login
  router.get("/", (req: Request, res: Response) => {
    // Check if user is already authenticated
    const user = (req.session as any)?.user;
    if (user) {
      // Redirect authenticated users to their dashboard
      const redirectUrl = user.role === 'admin' ? '/admin/dashboard' : 
                         user.role === 'manager' ? '/manager/dashboard' : 
                         '/driver/dashboard';
      return res.redirect(redirectUrl);
    }
    // Redirect unauthenticated users to login
    res.redirect('/auth/login');
  });

  // Serve static assets for auth pages (secure)
  router.use('/auth/static', (req, res, next) => {
    // Security: Use express.static with a fixed root to prevent path traversal
    const staticPath = path.join(__dirname, 'views');
    import('express').then(express => {
      const staticHandler = express.static(staticPath, { index: false });
      staticHandler(req, res, next);
    }).catch(next);
  });

  // GET route for login page
  router.get("/auth/login", (req: Request, res: Response) => {
    try {
      const authHtmlPath = path.join(__dirname, 'views', 'auth.html');
      res.sendFile(authHtmlPath);
    } catch (error) {
      console.error("Error serving login page:", error);
      res.status(500).json({ error: "Internal server error" });
    }
  });

  // GET route for signup page
  router.get("/auth/signup", (req: Request, res: Response) => {
    try {
      const authHtmlPath = path.join(__dirname, 'views', 'auth.html');
      res.sendFile(authHtmlPath);
    } catch (error) {
      console.error("Error serving signup page:", error);
      res.status(500).json({ error: "Internal server error" });
    }
  });

  // Admin dashboard route
  router.get("/admin/dashboard", requireAuth, requireRole(['admin']), (req: Request, res: Response) => {
    try {
      const user = (req.session as any)?.user;
      const adminHtmlPath = path.join(__dirname, 'views', 'admin-dashboard.html');
      res.sendFile(adminHtmlPath);
    } catch (error) {
      console.error("Error serving admin dashboard:", error);
      res.status(500).json({ error: "Internal server error" });
    }
  });

  // Manager dashboard route
  router.get("/manager/dashboard", requireAuth, requireRole(['manager', 'admin']), (req: Request, res: Response) => {
    try {
      const user = (req.session as any)?.user;
      const managerHtmlPath = path.join(__dirname, 'views', 'manager-dashboard.html');
      res.sendFile(managerHtmlPath);
    } catch (error) {
      console.error("Error serving manager dashboard:", error);
      res.status(500).json({ error: "Internal server error" });
    }
  });

  // Driver dashboard route
  router.get("/driver/dashboard", requireAuth, requireRole(['driver', 'admin', 'manager']), (req: Request, res: Response) => {
    try {
      const user = (req.session as any)?.user;
      const driverHtmlPath = path.join(__dirname, 'views', 'driver-dashboard.html');
      res.sendFile(driverHtmlPath);
    } catch (error) {
      console.error("Error serving driver dashboard:", error);
      res.status(500).json({ error: "Internal server error" });
    }
  });

  // POST route for sending OTP
  router.post("/auth/send-otp", async (req: Request, res: Response) => {
    try {
      const validatedData = sendOTPSchema.parse(req.body);
      const { phoneNumber, type, fullName, email } = validatedData;

      // Clean phone number
      const cleanPhone = phoneNumber.replace(/\s+/g, '').replace(/[^\d+]/g, '');
      
      // Generate 6-digit OTP
      const otpCode = Math.floor(100000 + Math.random() * 900000).toString();
      
      // Set expiration time (5 minutes from now)
      const expiresAt = new Date(Date.now() + 5 * 60 * 1000);

      // TODO: Integrate with Twilio SMS service using environment variables
      const accountSid = process.env.TWILIO_ACCOUNT_SID;
      const authToken = process.env.TWILIO_AUTH_TOKEN;
      const fromNumber = process.env.TWILIO_PHONE_NUMBER;

      if (!accountSid || !authToken || !fromNumber) {
        console.warn("Twilio credentials not configured, logging OTP instead");
        console.log(`OTP for ${cleanPhone}: ${otpCode}`);
      } else {
        // TODO: Implement actual Twilio SMS sending
        console.log(`Would send OTP ${otpCode} to ${cleanPhone} via Twilio`);
      }

      // Store OTP in session or database
      // For now, we'll use session storage
      if (!req.session) {
        req.session = {};
      }
      
      req.session.pendingOTP = {
        phoneNumber: cleanPhone,
        code: otpCode,
        expiresAt: expiresAt.toISOString(),
        attempts: 0,
        type,
        fullName,
        email
      };

      res.json({ 
        success: true, 
        message: "OTP sent successfully",
        maskedPhone: maskPhoneNumber(cleanPhone)
      });

    } catch (error) {
      console.error("Error sending OTP:", error);
      if (error instanceof z.ZodError) {
        res.status(400).json({ 
          error: "Validation error", 
          details: error.errors 
        });
      } else {
        res.status(500).json({ error: "Failed to send OTP" });
      }
    }
  });

  // POST route for verifying OTP
  router.post("/auth/verify-otp", async (req: Request, res: Response) => {
    try {
      const validatedData = verifyOTPSchema.parse(req.body);
      const { phoneNumber, code, type } = validatedData;

      const pendingOTP = req.session?.pendingOTP;
      
      if (!pendingOTP) {
        return res.status(400).json({ error: "No pending OTP found" });
      }

      // Check if OTP expired
      if (new Date() > new Date(pendingOTP.expiresAt)) {
        return res.status(400).json({ error: "OTP has expired" });
      }

      // Check if phone numbers match
      const cleanPhone = phoneNumber.replace(/\s+/g, '').replace(/[^\d+]/g, '');
      if (pendingOTP.phoneNumber !== cleanPhone) {
        return res.status(400).json({ error: "Phone number mismatch" });
      }

      // Increment attempts
      pendingOTP.attempts = (pendingOTP.attempts || 0) + 1;

      // Check max attempts
      if (pendingOTP.attempts > 3) {
        delete req.session.pendingOTP;
        return res.status(400).json({ error: "Too many attempts. Please request a new OTP." });
      }

      // Verify OTP code
      if (pendingOTP.code !== code) {
        return res.status(400).json({ 
          error: "Invalid OTP", 
          attemptsRemaining: 3 - pendingOTP.attempts 
        });
      }

      // OTP verified successfully
      delete req.session.pendingOTP;

      // TODO: Create or authenticate user in database
      // Determine user role based on phone number for demo purposes
      let userRole = 'driver'; // Default role
      if (cleanPhone === '+919999999999' || cleanPhone === '+91999999999' || cleanPhone === '9999999999') {
        userRole = 'admin'; // Demo admin user
      } else if (cleanPhone === '+918888888888' || cleanPhone === '+91888888888' || cleanPhone === '8888888888') {
        userRole = 'manager'; // Demo manager user
      }
      
      const userData = {
        id: generateUserId(),
        phoneNumber: cleanPhone,
        fullName: pendingOTP.fullName,
        email: pendingOTP.email,
        role: userRole as 'admin' | 'manager' | 'driver',
        isVerified: true,
        createdAt: new Date()
      };

      // Upsert user to storage - check if exists first
      let storageUser;
      try {
        // Try to find existing user by phone number
        storageUser = await app.locals.storage.getUserByUsername(cleanPhone);
        
        if (storageUser) {
          console.log(`Existing user found: ${storageUser.id} (${cleanPhone})`);
          // Update session with storage user ID to maintain consistency
          userData.id = storageUser.id;
        } else {
          // Create new user if doesn't exist
          storageUser = await app.locals.storage.createUser({
            phoneNumber: cleanPhone,
            username: cleanPhone, // Use phone as username
            fullName: userData.fullName,
            email: userData.email,
            role: userData.role as 'driver' | 'admin' | 'customer',
            isVerified: userData.isVerified
          });
          console.log(`New user created: ${storageUser.id} (${cleanPhone})`);
          // Update session with storage user ID
          userData.id = storageUser.id;
        }
      } catch (error) {
        console.error("Error upserting user to storage:", error);
        // Continue with session-only for backward compatibility
      }

      // Store user session with consistent storage ID
      req.session.user = userData;

      res.json({ 
        success: true, 
        message: "OTP verified successfully",
        user: {
          id: userData.id,
          phoneNumber: userData.phoneNumber,
          fullName: userData.fullName,
          email: userData.email,
          role: userData.role
        },
        redirectUrl: userData.role === 'admin' ? '/admin/dashboard' : 
                    userData.role === 'manager' ? '/manager/dashboard' : 
                    '/driver/dashboard'
      });

    } catch (error) {
      console.error("Error verifying OTP:", error);
      if (error instanceof z.ZodError) {
        res.status(400).json({ 
          error: "Validation error", 
          details: error.errors 
        });
      } else {
        res.status(500).json({ error: "Failed to verify OTP" });
      }
    }
  });

  // POST route for resending OTP
  router.post("/auth/resend-otp", async (req: Request, res: Response) => {
    try {
      const validatedData = resendOTPSchema.parse(req.body);
      const { phoneNumber } = validatedData;

      const pendingOTP = req.session?.pendingOTP;
      
      if (!pendingOTP) {
        return res.status(400).json({ error: "No pending OTP found" });
      }

      // Check if phone numbers match
      const cleanPhone = phoneNumber.replace(/\s+/g, '').replace(/[^\d+]/g, '');
      if (pendingOTP.phoneNumber !== cleanPhone) {
        return res.status(400).json({ error: "Phone number mismatch" });
      }

      // Generate new OTP
      const otpCode = Math.floor(100000 + Math.random() * 900000).toString();
      const expiresAt = new Date(Date.now() + 5 * 60 * 1000);

      // TODO: Send via Twilio
      console.log(`Resend OTP for ${cleanPhone}: ${otpCode}`);

      // Update session
      req.session.pendingOTP = {
        ...pendingOTP,
        code: otpCode,
        expiresAt: expiresAt.toISOString(),
        attempts: 0
      };

      res.json({ 
        success: true, 
        message: "OTP resent successfully" 
      });

    } catch (error) {
      console.error("Error resending OTP:", error);
      if (error instanceof z.ZodError) {
        res.status(400).json({ 
          error: "Validation error", 
          details: error.errors 
        });
      } else {
        res.status(500).json({ error: "Failed to resend OTP" });
      }
    }
  });

  // Logout route (POST)
  router.post("/auth/logout", (req: Request, res: Response) => {
    req.session?.destroy((err) => {
      if (err) {
        console.error("Error destroying session:", err);
        return res.status(500).json({ error: "Failed to logout" });
      }
      res.json({ success: true, message: "Logged out successfully" });
    });
  });

  // Logout route (GET) - for convenient logout links
  router.get("/auth/logout", (req: Request, res: Response) => {
    req.session?.destroy((err) => {
      if (err) {
        console.error("Error destroying session:", err);
        return res.status(500).send("Failed to logout");
      }
      res.redirect('/auth/login?message=logged-out');
    });
  });

  // Driver profile routes
  const uploadDir = path.join(__dirname, '..', 'uploads');
  mkdirSync(uploadDir, { recursive: true });
  
  const storage = multer.diskStorage({
    destination: uploadDir,
    filename: (req, file, cb) => {
      const userId = (req.session as any)?.user?.id || 'unknown';
      const timestamp = Date.now();
      const ext = path.extname(file.originalname);
      const baseName = path.basename(file.originalname, ext);
      cb(null, `${userId}_${file.fieldname}_${timestamp}_${baseName}${ext}`);
    }
  });
  
  const upload = multer({
    storage,
    limits: { fileSize: 16 * 1024 * 1024 }, // 16MB limit
    fileFilter: (req, file, cb) => {
      const allowedMimes = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'];
      if (allowedMimes.includes(file.mimetype)) {
        cb(null, true);
      } else {
        cb(new Error('Invalid file type. Only JPG, PNG, and PDF files are allowed.'));
      }
    }
  });

  // Driver profile form page
  router.get("/driver/profile", requireAuth, requireRole(['driver']), (req: Request, res: Response) => {
    try {
      const profileHtmlPath = path.join(__dirname, 'views', 'driver-profile.html');
      res.sendFile(profileHtmlPath);
    } catch (error) {
      console.error("Error serving driver profile page:", error);
      res.status(500).json({ error: "Internal server error" });
    }
  });

  // Driver profile API routes
  router.get("/api/driver/profile", requireAuth, requireRole(['driver']), async (req: Request, res: Response) => {
    try {
      const sessionUser = (req.session as any)?.user;
      const userId = sessionUser?.id; // Now consistent with storage ID
      
      const profile = await app.locals.storage.getDriverProfile(userId);
      res.json({ profile });
    } catch (error) {
      console.error("Error fetching driver profile:", error);
      res.status(500).json({ error: "Failed to fetch profile" });
    }
  });

  router.post("/api/driver/profile", 
    requireAuth, 
    requireRole(['driver']), 
    (req, res, next) => {
      console.log("POST /api/driver/profile - Request received");
      console.log("Headers:", req.headers);
      console.log("Session user:", (req.session as any)?.user);
      next();
    },
    upload.fields([
      { name: 'aadharFront', maxCount: 1 },
      { name: 'aadharBack', maxCount: 1 },
      { name: 'licenseFront', maxCount: 1 },
      { name: 'licenseBack', maxCount: 1 },
      { name: 'profilePhoto', maxCount: 1 }
    ]),
    async (req: Request, res: Response) => {
      try {
        console.log("Processing profile save request...");
        console.log("Request body:", req.body);
        console.log("Request files:", req.files);
        
        const sessionUser = (req.session as any)?.user;
        console.log("Session user from request:", sessionUser);
        
        const userId = sessionUser?.id; // Now consistent with storage ID
        console.log("User ID extracted:", userId);
        
        if (!userId) {
          console.log("ERROR: No user ID found in session");
          return res.status(401).json({ error: "User not authenticated" });
        }
        
        const files = req.files as { [fieldname: string]: Express.Multer.File[] };
        
        // Construct complete profile data with userId and file paths
        const profileData = {
          userId,
          fullName: req.body.fullName || '',
          phone: req.body.phone || sessionUser.phoneNumber,
          address: req.body.address || '',
          aadharNumber: req.body.aadharNumber || '',
          licenseNumber: req.body.licenseNumber || '',
          bankName: req.body.bankName,
          accountNumber: req.body.accountNumber,
          ifscCode: req.body.ifscCode,
          accountHolderName: req.body.accountHolderName,
          branchId: req.body.branchId,
          // Document file paths
          aadharFrontPath: files.aadharFront?.[0]?.filename,
          aadharBackPath: files.aadharBack?.[0]?.filename,
          licenseFrontPath: files.licenseFront?.[0]?.filename,
          licenseBackPath: files.licenseBack?.[0]?.filename,
          profilePhotoPath: files.profilePhoto?.[0]?.filename,
        };

        console.log("Profile data to validate:", profileData);

        // Validate with zod schema - userId is now included
        const validatedData = insertDriverProfileSchema.parse(profileData);
        
        // Save to storage
        const profile = await app.locals.storage.upsertDriverProfile(validatedData);
        
        console.log("Profile saved successfully:", profile.id);
        
        res.json({ 
          success: true, 
          message: "Profile saved successfully. Awaiting admin approval.",
          profile 
        });
      } catch (error) {
        console.error("Error saving driver profile:", error);
        if (error instanceof z.ZodError) {
          console.error("Validation errors:", error.errors);
          res.status(400).json({ error: "Invalid form data", details: error.errors });
        } else {
          res.status(500).json({ error: "Failed to save profile" });
        }
      }
    }
  );

  // Admin routes for driver management
  router.get("/admin/drivers", requireAuth, requireRole(['admin']), (req: Request, res: Response) => {
    try {
      const adminDriversHtmlPath = path.join(__dirname, 'views', 'admin-drivers.html');
      res.sendFile(adminDriversHtmlPath);
    } catch (error) {
      console.error("Error serving admin drivers page:", error);
      res.status(500).json({ error: "Internal server error" });
    }
  });

  router.get("/api/admin/drivers", requireAuth, requireRole(['admin']), async (req: Request, res: Response) => {
    try {
      const status = req.query.status as DriverStatus | undefined;
      const drivers = await app.locals.storage.listDriversByStatus(status);
      res.json({ drivers });
    } catch (error) {
      console.error("Error fetching drivers:", error);
      res.status(500).json({ error: "Failed to fetch drivers" });
    }
  });

  router.post("/api/admin/drivers/:userId/approve", requireAuth, requireRole(['admin']), async (req: Request, res: Response) => {
    try {
      const { userId } = req.params;
      const profile = await app.locals.storage.setDriverStatus(userId, DriverStatus.APPROVED);
      if (!profile) {
        return res.status(404).json({ error: "Driver profile not found" });
      }
      res.json({ success: true, message: "Driver approved successfully", profile });
    } catch (error) {
      console.error("Error approving driver:", error);
      res.status(500).json({ error: "Failed to approve driver" });
    }
  });

  router.post("/api/admin/drivers/:userId/reject", requireAuth, requireRole(['admin']), async (req: Request, res: Response) => {
    try {
      const { userId } = req.params;
      const profile = await app.locals.storage.setDriverStatus(userId, DriverStatus.REJECTED);
      if (!profile) {
        return res.status(404).json({ error: "Driver profile not found" });
      }
      res.json({ success: true, message: "Driver rejected", profile });
    } catch (error) {
      console.error("Error rejecting driver:", error);
      res.status(500).json({ error: "Failed to reject driver" });
    }
  });

  // Serve uploaded files
  router.use('/uploads', (req, res, next) => {
    // Security: Only authenticated users can access uploads
    if (!req.session?.user) {
      return res.status(401).json({ error: "Unauthorized" });
    }
    next();
  }, (req, res, next) => {
    const uploadsPath = path.join(__dirname, '..', 'uploads');
    import('express').then(express => {
      const staticHandler = express.static(uploadsPath, { index: false });
      staticHandler(req, res, next);
    }).catch(next);
  });

  app.use(router);
  return { close: () => {} }; // Return server-like object for compatibility
}

// Utility functions
function maskPhoneNumber(phone: string): string {
  if (phone.length >= 4) {
    const last4 = phone.slice(-4);
    const first = phone.slice(0, Math.max(0, phone.length - 6));
    return `${first} ****${last4}`;
  }
  return phone;
}

function generateUserId(): string {
  return 'user_' + Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
}

// Extend Express session type
declare module 'express-session' {
  interface SessionData {
    pendingOTP?: {
      phoneNumber: string;
      code: string;
      expiresAt: string;
      attempts: number;
      type: 'login' | 'signup';
      fullName?: string;
      email?: string;
    };
    user?: {
      id: string;
      phoneNumber: string;
      fullName?: string;
      email?: string;
      role: string;
      isVerified: boolean;
      createdAt: Date;
    };
  }
}
