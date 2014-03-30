from google.appengine.ext import ndb, blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import images

import webapp2
import jinja2
import random
import os

import logging

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class MemeModel(ndb.Model):
    image = ndb.BlobKeyProperty()
    date_added = ndb.DateTimeProperty(auto_now_add = True)
    rating_total = ndb.IntegerProperty(default = 0)
    rating_count = ndb.IntegerProperty(default = 0)
    rating = ndb.ComputedProperty(lambda self: (self.rating_total/self.rating_count if self.rating_count > 0 else 0) if self else None)

    
class IndexHandler(webapp2.RequestHandler):
    
    def get(self):
        """ Display a random meme to get rated """
        # Get all the memes in the datastore.
        # WARNING: This technicque is slow and will fail eventually, but its simple and works for small numbers of entries.
        meme_list = MemeModel.query().fetch(keys_only=True)

        # Choose a random index to get a key for
        random_meme = meme_list[random.randint(0, len(meme_list)-1)]

        try:
            meme = random_meme.get()

            #Set the template values
            template_values = {
                'meme': meme.key.urlsafe(),
                'title': "Rate this meme!",
                'image': images.get_serving_url(meme.image, size=400),
                'rating': meme.rating,
                'upload_url': blobstore.create_upload_url('/add')
            }
        except Exception:
            template_values = {
                'title': "No memes found!",
                'upload_url': blobstore.create_upload_url('/add')
            }

        # Get the template for the page
        template = JINJA_ENVIRONMENT.get_template('page.htm')

        # Output the data to the browser/client
        self.response.out.write(template.render(template_values))
        
        
class MemeUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
        
    def post(self):
        """ Accept a new meme upload """
        
        # Get the file we just uploaded - it has been automatically stored for us, we get a reference to it. 
        upload_files = self.get_uploads()
        logging.info(upload_files)
        blob_info = upload_files[0]

        # Create a new database entry to describe this meme
        new_meme = MemeModel(image = blob_info.key())

        # Commit this meme to the datastore
        new_meme.put()

        #Set the template values
        template_values = {
            'title': "Be the first to rate your new meme!",
            'meme': new_meme.key.urlsafe(),
            'image': images.get_serving_url(new_meme.image, size=400),
            'rating': new_meme.rating
        }
        
        # Get the template for the page
        template = JINJA_ENVIRONMENT.get_template('page.htm')
        
        # Output the data to the browser/client
        self.response.out.write(template.render(template_values))
        
class MemeRatingHandler(webapp2.RequestHandler):
    
    def post(self, meme = None):
        """ Accept a new meme rating. """
        # Grab the key from the URL to find the correct meme to rate. 
        meme_key = ndb.Key(urlsafe=meme)

        # Get the new rating.
        rating = self.request.POST.get('rating', None)

        # Get the meme entity from the datastore
        meme = meme_key.get()

        # Do some error checks
        if not rating:
            raise ValueError('rating')

        if not meme:
            raise IndexError('meme')

        meme.rating_total += int(rating)
        meme.rating_count += 1

        # Commit these changes
        meme.put()
        
        #Set the template values
        template_values = {
            'title': "Your rating has now been counted!",
            'meme': meme.key.urlsafe(),
            'image': images.get_serving_url(meme.image, size=400),
            'rating': meme.rating
        }
        
        # Get the template for the page
        template = JINJA_ENVIRONMENT.get_template('page.htm')
        
        # Output the data to the browser/client
        self.response.out.write(template.render(template_values))
        
        
application = webapp2.WSGIApplication([
    webapp2.Route(r'/rate/<meme>',          handler = MemeRatingHandler),
    webapp2.Route(r'/add',                  handler = MemeUploadHandler),
    webapp2.Route(r'/',                     handler = IndexHandler)
])