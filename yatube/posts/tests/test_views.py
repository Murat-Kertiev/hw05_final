from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Comment, Follow, Group, Post

User = get_user_model()

TEST_OF_POST: int = 13


class ViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='StasBasov')
        cls.user2 = User.objects.create_user(username='KertievMurat')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Тестовый комментарий',
        )
        cls.pages = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': f'{cls.group.slug}'}),
            reverse('posts:profile',
                    kwargs={'username': f'{cls.user.username}'})
        ]

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = [
            ('posts/index.html', reverse('posts:index')),
            ('posts/group_list.html',
             reverse('posts:group_list', kwargs={'slug': self.group.slug})),
            ('posts/profile.html',
             reverse('posts:profile',
                     kwargs={'username': self.post.author.username})),
            ('posts/post_detail.html',
             reverse('posts:post_detail', kwargs={'post_id': self.post.pk})),
            ('posts/create_post.html', reverse('posts:post_create')),
            ('posts/create_post.html',
             reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        ]
        for template, reverse_name in templates_pages_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        post_text_0 = {
            response.context['post'].text: 'Тестовый пост',
            response.context['post'].group: self.group,
            response.context['post'].author: self.user.username
        }
        for value, expected in post_text_0.items():
            self.assertEqual(post_text_0[value], expected)

    def test_post_edit_page_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_added_correctly(self):
        """Пост при создании добавлен корректно"""
        for page in self.pages:
            response = self.authorized_client.get(page)
            self.assertIn(self.post, response.context['page_obj'])

    def test_post_added_correctly_user2(self):
        """Пост при создании не добавляется другому пользователю,
           но виден на главной и в группе"""
        group2 = Group.objects.create(title='Тестовая группа 2',
                                      slug='test_group2')
        posts_count = Post.objects.filter(group=self.group).count()
        post = Post.objects.create(
            text='Тестовый пост от другого автора',
            author=self.user2,
            group=group2
        )
        response_profile = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': f'{self.user.username}'}))
        group = Post.objects.filter(group=self.group).count()
        self.assertEqual(group, posts_count)
        self.assertNotIn(post, response_profile.context['page_obj'])

    def test_comment_in_post_detail(self):
        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertIn('comments', response.context)

    def test_pages_uses_correct_template(self):
        """Кэширование данных на главной странице работает корректно"""
        response = self.guest_client.get(self.pages[0])
        cached_response_content = response.content
        Post.objects.create(text='Второй пост', author=self.user)
        response = self.guest_client.get(self.pages[0])
        self.assertEqual(cached_response_content, response.content)
        cache.clear()
        response = self.guest_client.get(self.pages[0])
        self.assertNotEqual(cached_response_content, response.content)

    def test_new_post_follow(self):
        """ Новая запись пользователя будет в ленте у тех кто на него
            подписан.
        """
        following = User.objects.create(username='following')
        Follow.objects.create(user=self.user, author=following)
        post = Post.objects.create(author=following, text=self.post.text)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertIn(post, response.context['page_obj'].object_list)

    def test_new_post_unfollow(self):
        """
        Новая запись пользователя не будет у тех кто не подписан на него.
        """
        self.client.logout()
        User.objects.create_user(
            username='somobody_temp',
            password='pass'
        )
        self.client.login(username='somobody_temp')
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotIn(
            self.post.text,
            response.context['page_obj'].object_list
        )

    def test_unfollow_another_user(self):
        """
        Авторизованный пользователь
        может удалять других пользователей из подписок
        """
        Follow.objects.create(user=self.user, author=self.user2)
        follow_count = Follow.objects.count()
        self.assertTrue(Follow.objects.filter(user=self.user,
                                              author=self.user2).exists())
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.user2}
            )
        )
        self.assertFalse(
            Follow.objects.filter(
                user=self.user,
                author=self.user2
            ).exists()
        )
        self.assertEqual(Follow.objects.count(), follow_count - 1)

    def test_follow_another_user(self):
        """
        Авторизованный пользователь,
        может подписываться на других пользователей
        """
        follow_count = Follow.objects.count()
        self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={'username': self.user2})
        )
        self.assertTrue(Follow.objects.filter(user=self.user,
                                              author=self.user2).exists())
        self.assertEqual(Follow.objects.count(), follow_count + 1)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        list_post: list = []
        for i in range(TEST_OF_POST):
            list_post.append(
                Post(text=f'Тестовый текст {i}',
                     group=cls.group,
                     author=cls.user)
            )
        Post.objects.bulk_create(list_post)
        cls.pages = [
            reverse('posts:index'),
            reverse('posts:profile',
                    kwargs={'username': f'{cls.user.username}'}),
            reverse('posts:group_list',
                    kwargs={'slug': f'{cls.group.slug}'})
        ]

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_correct_page_context_guest_client(self):
        """Проверка количества постов на первой и второй страницах
        для не авторизованного пользователя.
        """
        for page in self.pages:
            response1 = self.guest_client.get(page)
            response2 = self.guest_client.get(page + '?page=2')
            self.assertEqual(len(response1.context['page_obj']), 10)
            self.assertEqual(len(response2.context['page_obj']), 3)

    def test_correct_page_context_authorized_client(self):
        """Проверка количества постов на первой и второй страницах
        для авторизованного пользователя.
        """
        for page in self.pages:
            response1 = self.authorized_client.get(page)
            response2 = self.authorized_client.get(page + '?page=2')
            self.assertEqual(len(response1.context['page_obj']), 10)
            self.assertEqual(len(response2.context['page_obj']), 3)
