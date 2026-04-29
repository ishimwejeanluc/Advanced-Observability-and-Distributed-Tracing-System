pipeline {
    agent any 

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timestamps()
        timeout(time: 1, unit: 'HOURS')
    }

    environment {
        IMAGE_TAG = "${env.BUILD_NUMBER}"
    }

    stages {

        stage('Prepare .env') {
            steps {
                withCredentials([file(credentialsId: 'app_env_file1', variable: 'APP_ENV_FILE')]) {
                    sh '''
                        cp "$APP_ENV_FILE" .env
                        chmod 600 .env
                    '''
                }
            }
        }

        stage('Checkout') {
            steps {
                echo 'Checking out code...'
                checkout scm
            }
        }

        stage('Docker Build & Push') {
            steps {
                echo 'Building and pushing Docker image...'
                withCredentials([
                    file(credentialsId: 'app_env_file1', variable: 'APP_ENV_FILE'),
                    usernamePassword(credentialsId: 'dockerhub-credentials', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')
                ]) {
                    script {
                        def props = readProperties file: '.env'
                        def dockerRepo = props['DOCKER_HUB_REPO']
                        def imageName = "${DOCKER_USER}/${dockerRepo}"
                        def tag = env.IMAGE_TAG
                        def customImage = docker.build("${imageName}:${tag}", "-f web/Dockerfile web")
                        docker.withRegistry('https://index.docker.io/v1/', 'dockerhub-credentials') {
                            customImage.push()
                        }
                        writeFile file: 'docker_image.txt', text: imageName
                    }
                }
            }
        }

        stage('Deploy to EC2') {
            steps {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'ec2_ssh2',
                        keyFileVariable: 'ANSIBLE_SSH_KEY',
                        usernameVariable: 'ANSIBLE_SSH_USER'
                    )
                ]) {
                    script {
                        def props = readProperties file: '.env'
                        def ec2Ip = props['EC2_PUBLIC_IP']
                        def image = readFile('docker_image.txt').trim()
                        // Copy .env securely to EC2
                        sh '''
                            scp -o StrictHostKeyChecking=no -i "$ANSIBLE_SSH_KEY" .env "$ANSIBLE_SSH_USER"@$ec2Ip:/tmp/.env
                        '''
                        // Run ansible-playbook, passing only non-secret args
                        sh '''
                            ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook \
                                -i "$ec2Ip," \
                                -u "$ANSIBLE_SSH_USER" \
                                --private-key "$ANSIBLE_SSH_KEY" \
                                ansible/main.yml \
                                -e "web_image=$image:${env.IMAGE_TAG}" \
                                -e "env_file=/tmp/.env"
                        '''
                        // Remove .env from EC2 after deploy (optional, for extra safety)
                        sh '''
                            ssh -o StrictHostKeyChecking=no -i "$ANSIBLE_SSH_KEY" "$ANSIBLE_SSH_USER"@$ec2Ip 'rm -f /tmp/.env'
                        '''
                    }
                }
            }
        }

        stage('Cleanup') {
            steps {
                sh 'rm -f .env docker_image.txt || true'
                sh 'docker image prune -f || true'
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        success {
            echo "Pipeline completed successfully."
        }
        failure {
            echo "Pipeline failed. Check logs for details."
        }
    }
}