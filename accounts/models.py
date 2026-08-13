from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        
        # The first user created should default to ADMIN
        if not self.model.objects.exists():
            extra_fields.setdefault('role', 'admin')
            
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class Role(models.TextChoices):
    ADMIN = 'admin', 'College Placement Admin'
    STUDENT = 'trainee', 'Candidate Student'
    RECRUITER = 'recruiter', 'Corporate Recruiter Partner'
    PLACEMENT_OFFICER = 'trainer', 'Placement Officer'

Role.TRAINEE = Role.STUDENT
Role.TRAINER = Role.PLACEMENT_OFFICER

class CustomUser(AbstractUser):
    username = None  # Remove username field since email is used as username
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.STUDENT)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    @property
    def profile(self):
        return self

    def __str__(self):
        return f"{self.email} ({self.role})"


class UserProfile(CustomUser):
    class Meta:
        proxy = True


class Course(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name


class TraineeProfile(models.Model):
    class DegreeChoices(models.TextChoices):
        BTECH = 'BTECH', 'Bachelor of Technology (B.Tech)'
        MTECH = 'MTECH', 'Master of Technology (M.Tech)'
        MCA = 'MCA', 'Master of Computer Applications (MCA)'
        MBA = 'MBA', 'Master of Business Administration (MBA)'

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='trainee_profile')
    usn = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Unique Student Number")
    courses = models.ManyToManyField(Course, blank=True, related_name='students')
    
    # Personal Info
    profile_image = models.ImageField(upload_to='student_photos/', blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    portfolio_website = models.URLField(blank=True, null=True)

    # Training Info
    batch_code = models.CharField(max_length=50, blank=True, null=True)
    batch_start_date = models.DateField(blank=True, null=True)
    batch_end_date = models.DateField(blank=True, null=True)
    current_status = models.CharField(
        max_length=50, 
        choices=[('Training', 'Training'), ('Placement Ready', 'Placement Ready'), ('Placed', 'Placed'), ('Alumni', 'Alumni')], 
        default='Training'
    )
    course_completion = models.JSONField(default=dict)

    # New Course Details fields
    batch_timing = models.CharField(
        max_length=20, 
        choices=[('Morning', 'Morning'), ('Afternoon', 'Afternoon'), ('Evening', 'Evening')], 
        blank=True, 
        null=True
    )
    joining_date = models.DateField(blank=True, null=True)
    expected_completion_date = models.DateField(blank=True, null=True)
    
    is_course_editable = models.BooleanField(default=False)
    course_edit_request_status = models.CharField(
        max_length=20, 
        choices=[('none', 'No Request'), ('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected')], 
        default='none'
    )

    # Academic Info
    degree = models.CharField(max_length=100, default="MCA")
    branch = models.CharField(max_length=100, default="Computer Science & Engineering")
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)

    # New Academic Details
    tenth_school = models.CharField(max_length=150, blank=True, null=True)
    tenth_board = models.CharField(max_length=100, blank=True, null=True)
    tenth_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    tenth_year = models.IntegerField(blank=True, null=True)

    twelfth_college = models.CharField(max_length=150, blank=True, null=True)
    twelfth_board = models.CharField(max_length=100, blank=True, null=True)
    twelfth_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    twelfth_year = models.IntegerField(blank=True, null=True)

    graduation_college = models.CharField(max_length=150, blank=True, null=True)
    graduation_university = models.CharField(max_length=150, blank=True, null=True)
    graduation_year = models.IntegerField(blank=True, null=True)

    has_post_graduation = models.BooleanField(default=False)
    pg_college = models.CharField(max_length=150, blank=True, null=True)
    pg_university = models.CharField(max_length=150, blank=True, null=True)
    pg_degree = models.CharField(max_length=100, blank=True, null=True)
    pg_branch = models.CharField(max_length=100, blank=True, null=True)
    pg_cgpa = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    pg_year = models.IntegerField(blank=True, null=True)

    # Professional Info
    skills = models.JSONField(default=list)
    certifications = models.JSONField(default=list)
    internships = models.JSONField(default=list)
    projects = models.JSONField(default=list)
    experience_years = models.IntegerField(default=0, blank=True, verbose_name="Years of Experience")

    # Scorecard indexes
    placement_readiness_score = models.IntegerField(default=70)
    is_accredited_for_placement = models.BooleanField(default=True)
    approval_status = models.CharField(
        max_length=15,
        choices=[('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )
    
    # Resume Info
    resume_file = models.FileField(upload_to='student_resumes/', blank=True, null=True)
    resume_uploaded_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def profile_completion_percentage(self):
        attributes = [
            self.user.first_name if self.user else None, 
            self.user.last_name if self.user else None, 
            self.user.email if self.user else None,
            self.phone_number, self.address, self.profile_image, 
            self.degree, self.branch, self.cgpa, self.skills, 
            self.certifications, self.internships, self.resume_file
        ]
        filled = sum(1 for attr in attributes if attr)
        return int((filled / len(attributes)) * 100)

    def get_degree_display(self):
        return self.degree

    def __str__(self):
        return f"{self.user.email if self.user else 'No User'} ({self.usn})"


class RecruiterProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='recruiter_profile')
    company_name = models.CharField(max_length=150, unique=True, verbose_name="Enterprise Corporate Identity Name")
    industry_domain = models.CharField(max_length=100, default="Information Technology")
    company_website = models.URLField(blank=True, null=True)
    contact_email = models.EmailField()
    about_company = models.TextField(blank=True, null=True)
    is_approved_by_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company_name} - {self.user.email if self.user else 'No User'}"

class TrainerProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='trainer_profile')
    is_approved = models.BooleanField(default=False)
    courses_handled = models.ManyToManyField(Course, blank=True, related_name='placement_officers')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} (Approved: {self.is_approved})"

StudentProfile = TraineeProfile
PlacementOfficerProfile = TrainerProfile
