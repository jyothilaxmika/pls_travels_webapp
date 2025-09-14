import { Request, Response, Router } from "express";
import { z } from "zod";
import path from "path";
import { fileURLToPath } from "url";
import { sendOTPSchema, verifyOTPSchema, resendOTPSchema } from "@shared/schema";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export function registerRoutes(app: any) {
  const router = Router();

  // Serve static assets for auth pages
  router.use('/auth/static', (req, res, next) => {
    const filePath = path.join(__dirname, 'views', req.path);
    res.sendFile(filePath, (err) => {
      if (err) {
        next();
      }
    });
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
      const userData = {
        id: generateUserId(),
        phoneNumber: cleanPhone,
        fullName: pendingOTP.fullName,
        email: pendingOTP.email,
        role: 'customer' as const,
        isVerified: true,
        createdAt: new Date()
      };

      // Store user session
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
        redirectUrl: '/dashboard'
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

  // Logout route
  router.post("/auth/logout", (req: Request, res: Response) => {
    req.session?.destroy((err) => {
      if (err) {
        console.error("Error destroying session:", err);
        return res.status(500).json({ error: "Failed to logout" });
      }
      res.json({ success: true, message: "Logged out successfully" });
    });
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
