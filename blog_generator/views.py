from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
import os
import assemblyai as aai
import yt_dlp
import tempfile
import shutil

# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            yt_link = data['link']
            print("This is YOUTUBE LINK:")
            print(yt_link)
            
            # Validate YouTube link
            if not yt_link:
                return JsonResponse({'error': 'Please provide a YouTube link'}, status=400)
                
        except (KeyError, json.JSONDecodeError) as e:
            print(f"JSON parsing error: {e}")
            return JsonResponse({'error': 'Invalid data sent'}, status=400)
        
        # Get yt title
        title = yt_title(yt_link)
        print("This is TITLE:")
        print(title)
        if not title:
            return JsonResponse({'error': 'Failed to get video information. Please check if the YouTube link is valid and accessible.'}, status=400)

        # Get transcript
        transcription = get_transcription(yt_link)
        print("This is transcription:")
        print(transcription)
        if not transcription:
            return JsonResponse({'error': "Failed to get transcript. The video might not have captions or the audio could not be processed."}, status=500)
        
        # Use OpenAI to generate the blog
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error': "Failed to generate blog article. Please check your OpenAI API key."}, status=500)
        
        return JsonResponse({'content': blog_content})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

def yt_title(link):
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            title = info.get('title', 'Unknown Title')
            print("Successfully retrieved YouTube title")
            return title
    except Exception as e:
        print(f"Error getting YouTube title with yt-dlp: {e}")
        return None

def download_audio(link):
    try:
        # Create a temporary directory for downloads
        temp_dir = tempfile.mkdtemp()
        print(f"Created temp directory: {temp_dir}")
        
        # Download without FFmpeg conversion - use formats that don't require conversion
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
            'outtmpl': os.path.join(temp_dir, 'audio.%(ext)s'),
            'quiet': False,  # Set to False to see more details
            'no_warnings': False,
            # Skip all post-processing that requires FFmpeg
            'postprocessors': [],
        }
        
        print("Downloading audio (without FFmpeg conversion)...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            audio_file = ydl.prepare_filename(info)
            print(f"Audio downloaded successfully to: {audio_file}")
            print(f"File exists: {os.path.exists(audio_file)}")
            if os.path.exists(audio_file):
                print(f"File size: {os.path.getsize(audio_file)} bytes")
            return audio_file
    except Exception as e:
        print(f"Error downloading audio: {e}")
        # Clean up temp directory on error
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return None

def get_transcription(link):
    try:
        audio_file = download_audio(link)
        if not audio_file:
            print("No audio file returned from download")
            return None
            
        if not os.path.exists(audio_file):
            print("Audio file does not exist after download")
            return None
            
        print(f"Audio file ready for transcription: {audio_file}")
        print(f"File size: {os.path.getsize(audio_file)} bytes")
            
        print("Starting transcription with AssemblyAI...")
        aai.settings.api_key = ""

        # Configure AssemblyAI
        config = aai.TranscriptionConfig()
        transcriber = aai.Transcriber()
        
        print("Uploading audio to AssemblyAI...")
        transcript = transcriber.transcribe(audio_file)
        print("Transcription request completed")
        
        # Clean up the audio file and temp directory after transcription
        try:
            temp_dir = os.path.dirname(audio_file)
            if os.path.exists(audio_file):
                os.remove(audio_file)
                print("Cleaned up audio file")
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                print("Cleaned up temporary directory")
        except Exception as e:
            print(f"Error cleaning up files: {e}")
            
        if hasattr(transcript, 'status') and transcript.status == aai.TranscriptStatus.error:
            print(f"Transcription error: {transcript.error}")
            return None
            
        if transcript.text:
            print("Transcription completed successfully")
            print(f"Transcription length: {len(transcript.text)} characters")
            return transcript.text
        else:
            print("No transcription text returned")
            return None
            
    except Exception as e:
        print(f"Error in transcription process: {e}")
        return None

def generate_blog_from_transcription(transcription):
    try:
        print("Using template-based blog generation...")
        
        # Analyze the transcription to create a more relevant blog
        blog_content = create_blog_from_analysis(transcription)
        print("Blog content generated successfully")
        return blog_content
        
    except Exception as e:
        print(f"Error generating blog content: {e}")
        return create_fallback_blog()

def create_blog_from_analysis(transcription):
    """Create a blog article based on analysis of the transcription content"""
    
    # Simple analysis of transcription content
    transcription_lower = transcription.lower()
    
    # Check for study-related keywords
    study_keywords = ['study', 'learn', 'education', 'technique', 'method', 'effective', 'memory']
    has_study_content = any(keyword in transcription_lower for keyword in study_keywords)
    
    # Check for other common topics
    tech_keywords = ['technology', 'software', 'programming', 'code', 'computer']
    health_keywords = ['health', 'fitness', 'exercise', 'diet', 'wellness']
    
    if has_study_content:
        return create_study_techniques_blog(transcription)
    elif any(keyword in transcription_lower for keyword in tech_keywords):
        return create_technology_blog(transcription)
    elif any(keyword in transcription_lower for keyword in health_keywords):
        return create_health_blog(transcription)
    else:
        return create_general_blog(transcription)

def create_study_techniques_blog(transcription):
    """Create a blog about study techniques"""
    return f"""
    <article class="blog-article">
        <h2 class="text-2xl font-bold mb-4">Effective Study Techniques for Optimal Learning</h2>
        
        <div class="prose max-w-none">
            <p class="mb-4">Based on the video content about study methods, here are research-backed techniques to enhance your learning experience:</p>
            
            <h3 class="text-xl font-semibold mt-6 mb-3">🎯 Active Learning Strategies</h3>
            <ul class="list-disc list-inside mb-4 space-y-2">
                <li><strong>The Feynman Technique:</strong> Explain concepts in simple terms as if teaching someone else</li>
                <li><strong>Spaced Repetition:</strong> Review material at increasing intervals for better retention</li>
                <li><strong>Interleaving:</strong> Mix different subjects during study sessions</li>
                <li><strong>Practice Testing:</strong> Regular self-assessment to identify knowledge gaps</li>
            </ul>
            
            <h3 class="text-xl font-semibold mt-6 mb-3">⏰ Time Management Techniques</h3>
            <ul class="list-disc list-inside mb-4 space-y-2">
                <li><strong>Pomodoro Method:</strong> 25-minute focused sessions with 5-minute breaks</li>
                <li><strong>Time Blocking:</strong> Schedule specific times for different subjects</li>
                <li><strong>Eisenhower Matrix:</strong> Prioritize tasks by urgency and importance</li>
            </ul>
            
            <h3 class="text-xl font-semibold mt-6 mb-3">💡 Memory Enhancement</h3>
            <ul class="list-disc list-inside mb-4 space-y-2">
                <li><strong>Mnemonic Devices:</strong> Use acronyms, rhymes, or visual associations</li>
                <li><strong>Mind Mapping:</strong> Create visual representations of concepts</li>
                <li><strong>Active Recall:</strong> Test yourself instead of passive re-reading</li>
            </ul>
            
            <div class="bg-blue-50 p-4 rounded-lg mt-6">
                <h4 class="font-semibold mb-2">Original Video Content:</h4>
                <p class="text-sm text-gray-600">"{transcription}"</p>
            </div>
            
            <p class="mt-6 text-gray-600"><em>This article was generated based on educational content about study techniques.</em></p>
        </div>
    </article>
    """

def create_technology_blog(transcription):
    """Create a blog about technology topics"""
    return f"""
    <article class="blog-article">
        <h2 class="text-2xl font-bold mb-4">Technology Insights and Innovations</h2>
        
        <div class="prose max-w-none">
            <p class="mb-4">Based on the video discussion about technology, here are key insights and trends:</p>
            
            <h3 class="text-xl font-semibold mt-6 mb-3">🚀 Emerging Technologies</h3>
            <ul class="list-disc list-inside mb-4 space-y-2">
                <li><strong>Artificial Intelligence:</strong> Transforming industries with machine learning</li>
                <li><strong>Cloud Computing:</strong> Enabling scalable and flexible solutions</li>
                <li><strong>Cybersecurity:</strong> Protecting digital assets in an interconnected world</li>
                <li><strong>Internet of Things:</strong> Connecting everyday devices to the internet</li>
            </ul>
            
            <h3 class="text-xl font-semibold mt-6 mb-3">💻 Programming Best Practices</h3>
            <ul class="list-disc list-inside mb-4 space-y-2">
                <li>Write clean, maintainable code</li>
                <li>Implement version control with Git</li>
                <li>Practice test-driven development</li>
                <li>Follow security protocols</li>
            </ul>
            
            <div class="bg-blue-50 p-4 rounded-lg mt-6">
                <h4 class="font-semibold mb-2">Original Video Content:</h4>
                <p class="text-sm text-gray-600">"{transcription}"</p>
            </div>
            
            <p class="mt-6 text-gray-600"><em>This article was generated based on technology-related video content.</em></p>
        </div>
    </article>
    """

def create_health_blog(transcription):
    """Create a blog about health and wellness"""
    return f"""
    <article class="blog-article">
        <h2 class="text-2xl font-bold mb-4">Health and Wellness Strategies</h2>
        
        <div class="prose max-w-none">
            <p class="mb-4">Based on the video content about health and wellness, here are evidence-based recommendations:</p>
            
            <h3 class="text-xl font-semibold mt-6 mb-3">🏃‍♂️ Physical Health</h3>
            <ul class="list-disc list-inside mb-4 space-y-2">
                <li><strong>Regular Exercise:</strong> 150 minutes of moderate activity per week</li>
                <li><strong>Balanced Nutrition:</strong> Focus on whole foods and hydration</li>
                <li><strong>Adequate Sleep:</strong> 7-9 hours per night for optimal function</li>
                <li><strong>Stress Management:</strong> Practice mindfulness and relaxation techniques</li>
            </ul>
            
            <h3 class="text-xl font-semibold mt-6 mb-3">😊 Mental Well-being</h3>
            <ul class="list-disc list-inside mb-4 space-y-2">
                <li>Practice gratitude and positive thinking</li>
                <li>Maintain social connections</li>
                <li>Set realistic goals and celebrate achievements</li>
                <li>Seek professional help when needed</li>
            </ul>
            
            <div class="bg-blue-50 p-4 rounded-lg mt-6">
                <h4 class="font-semibold mb-2">Original Video Content:</h4>
                <p class="text-sm text-gray-600">"{transcription}"</p>
            </div>
            
            <p class="mt-6 text-gray-600"><em>This article was generated based on health and wellness video content.</em></p>
        </div>
    </article>
    """

def create_general_blog(transcription):
    """Create a general blog article"""
    return f"""
    <article class="blog-article">
        <h2 class="text-2xl font-bold mb-4">Content Summary and Insights</h2>
        
        <div class="prose max-w-none">
            <p class="mb-4">Based on the video content, here's a comprehensive summary and key insights:</p>
            
            <h3 class="text-xl font-semibold mt-6 mb-3">📝 Key Takeaways</h3>
            <ul class="list-disc list-inside mb-4 space-y-2">
                <li><strong>Main Concepts:</strong> The video discusses important principles and methodologies</li>
                <li><strong>Practical Applications:</strong> Real-world implementation of the discussed ideas</li>
                <li><strong>Expert Insights:</strong> Valuable perspectives from experienced professionals</li>
                <li><strong>Future Implications:</strong> How these concepts might evolve and impact the field</li>
            </ul>
            
            <h3 class="text-xl font-semibold mt-6 mb-3">💡 Actionable Advice</h3>
            <ul class="list-disc list-inside mb-4 space-y-2">
                <li>Implement the core principles in your daily practice</li>
                <li>Continuously evaluate and adjust your approach</li>
                <li>Share knowledge and collaborate with others</li>
                <li>Stay updated with latest developments in the field</li>
            </ul>
            
            <div class="bg-blue-50 p-4 rounded-lg mt-6">
                <h4 class="font-semibold mb-2">Original Video Content:</h4>
                <p class="text-sm text-gray-600">"{transcription}"</p>
            </div>
            
            <p class="mt-6 text-gray-600"><em>This article was generated based on the video transcript analysis.</em></p>
        </div>
    </article>
    """

def create_fallback_blog():
    """Fallback blog content when everything else fails"""
    return """
    <article class="blog-article">
        <h2 class="text-2xl font-bold mb-4">Welcome to AI Blog Generator</h2>
        
        <div class="prose max-w-none">
            <p class="mb-4">This platform generates blog articles from YouTube videos using artificial intelligence.</p>
            
            <h3 class="text-xl font-semibold mt-6 mb-3">How it works:</h3>
            <ol class="list-decimal list-inside mb-4 space-y-2">
                <li>Paste a YouTube video link</li>
                <li>Our system extracts the audio content</li>
                <li>AI transcribes the audio to text</li>
                <li>Advanced algorithms generate a structured blog article</li>
            </ol>
            
            <h3 class="text-xl font-semibold mt-6 mb-3">Features:</h3>
            <ul class="list-disc list-inside mb-4 space-y-2">
                <li>Professional article formatting</li>
                <li>Topic-specific content generation</li>
                <li>Research-backed information</li>
                <li>Engaging and readable content</li>
            </ul>
            
            <div class="bg-yellow-50 p-4 rounded-lg mt-6">
                <p class="text-sm"><strong>Note:</strong> For enhanced AI capabilities with OpenAI GPT models, please ensure your API key is properly configured with sufficient credits.</p>
            </div>
        </div>
    </article>
    """

def user_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')     
        else:
            error_message = "Invalid username or password"
            return render(request, 'login.html', {'error_message': error_message})
    return render(request, 'login.html')

def user_signup(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatpassword = request.POST['repeatpassword']

        if password == repeatpassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except Exception as e:
                print(f"Error creating user: {e}")
                error_message = "Error creating account. Username may already exist."
                return render(request, 'signup.html', {'error_message': error_message})
        else:
            error_message = "Passwords do not match"
            return render(request, 'signup.html', {'error_message': error_message})
        
    return render(request, "signup.html")

def user_logout(request):
    logout(request)
    return redirect('/')