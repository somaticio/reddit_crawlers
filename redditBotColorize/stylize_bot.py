import traceback
import argparse
import image_downloader
import image_uploader
import secret_keys
import praw
import time
import re
import database
import requests

parser = argparse.ArgumentParser()
parser.add_argument("--subreddit", help="which subreddit to use",
                    default="rickandmorty+funny+nonononono+ExpectationVsReality+aww+\
                    todayilearned+gaming+mildlyinteresting+Art+photoshopbattles+space+\
                    DIY+OldSchoolCool+creepy+Futurology+EarthPorn+UpliftingNews+\
                    sports+The_Donald+AdviceAnimals+atheism+europe+woahdude+interestingasfuck+\
                    BlackPeopleTwitter+pokemongo+pcmasterrace+ImGoingToHellForThis+pokemon")
args = parser.parse_args()
subreddit = args.subreddit
# Login to Reddit
reddit_account = praw.Reddit(secret_keys.reddit_bot_user_agent)
reddit_account.login(username=secret_keys.reddit_username,password=secret_keys.reddit_user_password)

upload_queue = []
upload_timer = time.time()
upload_timeout = 60*10

def verbose_print(msg,verbose = False):
    if verbose:
        print msg



def check_condition(c):
    text = c.body
    tokens = text.lower().split()
    if len(tokens)  == 1 and ("stylizebot" in tokens):
        return True

def stylize_and_upload_from_url(image_url,verbose=True):
    img_path = image_downloader.download_image(image_url)

    #didn't mange to download photo
    if len(img_path) == 0:
        print 'Problem downloading %s' % image_url
        return ''

    verbose_print(['link is : ', image_url, 'img_path is ',img_path],verbose)

    # Somatic api call
    url = "http://www.somatic.io/api/v1/random_style"
    files = {"--input": ('image.jpg', open(img_path, 'rb'),'image/jpeg')}
    data = {"api_key" : secret_keys.api_key} #import from secret_keys
    response = requests.post(url, data=data, files=files)
    if len(response.content) == 8:
        uploaded_stylized_image_url = "http://www.somatic.io/examples/" + response.content
    else:
        uploaded_stylized_image_url = ""
    print(uploaded_stylized_image_url)
    return uploaded_stylized_image_url


def bot_action(c, verbose=True):
    print(c.link_id)
    if not database.did_reply_thread(c.link_id):
        img_url = c.link_url

        stylized_image_url = stylize_and_upload_from_url(img_url)

        if len(stylized_image_url) == 0:
            print 'From bot action :: There was an error while trying to stylize and upload the photo , %s' % img_url
            return ''

        #Reply to the one who summned the bot
        elif 'already_stylized' in stylized_image_url:
            msg = 'Hi I\'m stylizebot. I was trained to stylize photos.\n\n Your photo seems to be already stylized, Please try uploading another photo. \n\n This is still a **beta-bot**.'
        else:
            msg = 'Hi I\'m stylizebot. I was trained to stylize photos.\n\n This is my attempt to stylize your image, here you go : %s \n\n This is still a **beta-bot**. '%(stylized_image_url)
        try:
            res = c.reply(msg)
            database.add_thread(c.link_id,c.link_url,stylized_image_url)
            database.add_comment(c.id)
        except:
            upload_queue.append((c,msg))
            traceback.print_exc()


def run_main_reddit_loop():
    global praw,database,upload_timer
    #list = ['rickandmorty', 'funny', 'pics', 'worldnews', 'food']
    #Main loop the listens to new comments on some subreddit
    #for subreddit in list:
    for c in praw.helpers.comment_stream(reddit_account, subreddit):
        if check_condition(c):
            if not database.did_reply_comment(c.id):
                submission = reddit_account.get_submission(submission_id=c.permalink)
                flat_comments = praw.helpers.flatten_tree(submission.comments)
                already_commented = False
                for comment in flat_comments:
                    if str(comment.author) == secret_keys.reddit_username:
                        database.add_comment(c.id)
                        database.add_thread(c.link_id,c.link_url,'')
                        already_commented = True
                        break
                if not already_commented:
                    bot_action(c)
        if (time.time() - upload_timer)  > upload_timeout :
            upload_timer = time.time()
            print "Trying to send a comment"
            try:
                reddit_comment,msg = upload_queue[0]
                print reddit_comment.permalink,msg
                reddit_comment.reply(msg)
                upload_queue.pop()
            except:
                pass

while True:
    try:
        run_main_reddit_loop()
    except:
        traceback.print_exc()
        reddit_account = praw.Reddit(secret_keys.reddit_bot_user_agent)
        reddit_account.login(username=secret_keys.reddit_username,password=secret_keys.reddit_user_password)
